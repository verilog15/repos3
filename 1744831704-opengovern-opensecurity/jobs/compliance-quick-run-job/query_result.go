package compliance_quick_run_job

import (
	"bytes"
	"fmt"
	authApi "github.com/opengovern/og-util/pkg/api"
	"github.com/opengovern/og-util/pkg/httpclient"
	"github.com/opengovern/og-util/pkg/integration"
	"github.com/opengovern/og-util/pkg/steampipe"
	"github.com/opengovern/opensecurity/pkg/types"
	"github.com/opengovern/opensecurity/services/compliance/api"
	coreApi "github.com/opengovern/opensecurity/services/core/api"
	"go.uber.org/zap"
	"golang.org/x/net/context"
	"text/template"
)

type QueryResult struct {
	ComplianceStatus   types.ComplianceStatus
	ResourceID         string
	PlatformResourceID string
	ResourceName       string
	ResourceType       string
	Reason             string
}

type ExecutionPlan struct {
	Policy    api.Policy
	ControlID string

	IntegrationIDs []string
}

type QueryJob struct {
	AuditJobID    uint
	ExecutionPlan ExecutionPlan
}

func (w *Worker) RunQuery(ctx context.Context, j QueryJob, queryParams *coreApi.ListQueryParametersResponse) ([]QueryResult, error) {
	w.logger.Info("Running query",
		zap.String("query_id", j.ExecutionPlan.Policy.ID),
		zap.Strings("integration_ids", j.ExecutionPlan.IntegrationIDs),
	)

	queryParamMap := make(map[string]string)
	for _, qp := range queryParams.Items {
		if qp.ControlID == "" {
			queryParamMap[qp.Key] = qp.Value
		} else if qp.ControlID == j.ExecutionPlan.ControlID {
			queryParamMap[qp.Key] = qp.Value
		}
	}

	for _, param := range j.ExecutionPlan.Policy.Parameters {
		if _, ok := queryParamMap[param.Key]; !ok && param.Required {
			w.logger.Error("required query parameter not found",
				zap.String("key", param.Key),
				zap.String("query_id", j.ExecutionPlan.Policy.ID),
				zap.Strings("integration_id", j.ExecutionPlan.IntegrationIDs),
			)
			return nil, fmt.Errorf("required query parameter not found: %s for query: %s", param.Key, j.ExecutionPlan.Policy.ID)
		}
		if _, ok := queryParamMap[param.Key]; !ok && !param.Required {
			w.logger.Info("optional query parameter not found",
				zap.String("key", param.Key),
				zap.String("query_id", j.ExecutionPlan.Policy.ID),
				zap.Strings("integration_id", j.ExecutionPlan.IntegrationIDs),
			)
			queryParamMap[param.Key] = ""
		}
	}

	res, err := w.runSqlWorkerJob(ctx, j, queryParamMap)

	if err != nil {
		w.logger.Error("failed to get results", zap.Error(err))
		return nil, err
	}

	w.logger.Info("Extracting and pushing to nats",
		zap.Int("res_count", len(res.Data)),
		zap.Any("res", *res),
		zap.String("query", j.ExecutionPlan.Policy.Definition),
		zap.String("query_id", j.ExecutionPlan.Policy.ID),
	)

	queryResults, err := w.ExtractQueryResult(w.logger, res, j.ExecutionPlan.Policy, j)
	if err != nil {
		return nil, err
	}

	return queryResults, nil
}

func (w *Worker) runSqlWorkerJob(ctx context.Context, j QueryJob, queryParamMap map[string]string) (*steampipe.Result, error) {
	queryTemplate, err := template.New(j.ExecutionPlan.Policy.ID).Parse(j.ExecutionPlan.Policy.Definition)
	if err != nil {
		w.logger.Error("failed to parse query template", zap.Error(err))
		return nil, err
	}
	var queryOutput bytes.Buffer
	if err := queryTemplate.Execute(&queryOutput, queryParamMap); err != nil {
		w.logger.Error("failed to execute query template",
			zap.Error(err),
			zap.String("query_id", j.ExecutionPlan.Policy.ID),
			zap.Strings("integration_id", j.ExecutionPlan.IntegrationIDs),
			zap.Uint("job_id", j.AuditJobID),
		)
		return nil, fmt.Errorf("failed to execute query template: %w for query: %s", err, j.ExecutionPlan.Policy.ID)
	}

	w.logger.Info("runSqlWorkerJob QueryOutput",
		zap.Uint("job_id", j.AuditJobID),
		zap.String("query", j.ExecutionPlan.Policy.Definition),
		zap.String("query_id", j.ExecutionPlan.Policy.ID),
		zap.String("query", queryOutput.String()))
	res, err := w.steampipeConn.QueryAll(ctx, queryOutput.String())
	if err != nil {
		w.logger.Error("failed to run query", zap.Error(err), zap.String("query_id", j.ExecutionPlan.Policy.ID), zap.Strings("integration_id", j.ExecutionPlan.IntegrationIDs))
		return nil, err
	}

	return res, nil
}

func (w *Worker) GetResourceTypeFromTableName(tableName string, queryIntegrationType []integration.Type) (string, error) {
	var integrationType integration.Type
	if len(queryIntegrationType) == 1 {
		integrationType = queryIntegrationType[0]
	} else {
		integrationType = ""
	}

	return w.integrationClient.GetResourceTypeFromTableName(&httpclient.Context{UserRole: authApi.AdminRole}, integrationType.String(), tableName)
}

func (w *Worker) ExtractQueryResult(_ *zap.Logger, res *steampipe.Result, query api.Policy, job QueryJob) ([]QueryResult, error) {
	var complianceResults []QueryResult
	var err error
	queryResourceType := ""
	if query.PrimaryResource != nil || len(query.ListOfResources) == 1 {
		tableName := ""
		if query.PrimaryResource != nil {
			tableName = *query.PrimaryResource
		} else {
			tableName = query.ListOfResources[0]
		}
		if tableName != "" && len(job.ExecutionPlan.Policy.IntegrationType) > 0 {
			queryResourceType, err = w.integrationClient.GetResourceTypeFromTableName(&httpclient.Context{UserRole: authApi.AdminRole}, job.ExecutionPlan.Policy.IntegrationType[0], tableName)
			if err != nil {
				return nil, err
			}
		}
	}

	for _, record := range res.Data {
		if len(record) != len(res.Headers) {
			return nil, fmt.Errorf("invalid record length, record=%d headers=%d", len(record), len(res.Headers))
		}
		recordValue := make(map[string]any)
		for idx, header := range res.Headers {
			value := record[idx]
			recordValue[header] = value
		}
		resourceType := queryResourceType

		var platformResourceID, resourceID, resourceName, reason string
		var status types.ComplianceStatus
		if v, ok := recordValue["platform_resource_id"].(string); ok {
			platformResourceID = v
		}
		if v, ok := recordValue["platform_table_name"].(string); ok && resourceType == "" && len(job.ExecutionPlan.Policy.IntegrationType) > 0 {
			resourceType, err = w.integrationClient.GetResourceTypeFromTableName(&httpclient.Context{UserRole: authApi.AdminRole}, job.ExecutionPlan.Policy.IntegrationType[0], v)
			if err != nil {
				return nil, err
			}
		}
		if v, ok := recordValue["resource"].(string); ok && v != "" && v != "null" {
			resourceID = v
		} else {
			continue
		}
		if v, ok := recordValue["name"].(string); ok {
			resourceName = v
		}
		if v, ok := recordValue["reason"].(string); ok {
			reason = v
		}
		if v, ok := recordValue["status"].(string); ok {
			status = types.ComplianceStatus(v)
		}

		if status != types.ComplianceStatusOK && status != types.ComplianceStatusALARM {
			continue
		}

		complianceResults = append(complianceResults, QueryResult{
			ComplianceStatus:   status,
			PlatformResourceID: platformResourceID,
			ResourceID:         resourceID,
			ResourceName:       resourceName,
			ResourceType:       resourceType,
			Reason:             reason,
		})
	}
	return complianceResults, nil
}
