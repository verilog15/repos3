package query_runner

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"text/template"

	"github.com/opengovern/og-util/pkg/api"
	"github.com/opengovern/og-util/pkg/httpclient"
	queryrunner "github.com/opengovern/opensecurity/jobs/query-runner-job"
	coreApi "github.com/opengovern/opensecurity/services/core/api"
	"go.uber.org/zap"
)

func (s *JobScheduler) runPublisher(ctx context.Context) error {
	ctx2 := &httpclient.Context{UserRole: api.AdminRole}
	ctx2.Ctx = ctx

	s.logger.Info("Policy Runner publisher started")

	err := s.db.UpdateTimedOutQueuedQueryRunners()
	if err != nil {
		s.logger.Error("failed to update timed out query runners", zap.Error(err))
	}

	err = s.db.UpdateTimedOutInProgressQueryRunners()
	if err != nil {
		s.logger.Error("failed to update timed out query runners", zap.Error(err))
	}

	jobs, err := s.db.FetchCreatedQueryRunnerJobs()
	if err != nil {
		s.logger.Error("Fetch Created Policy Runner Jobs Error", zap.Error(err))
		return err
	}
	s.logger.Info("Fetch Created Policy Runner Jobs", zap.Any("Jobs Count", len(jobs)))
	for _, job := range jobs {
		namedQuery, err := s.coreClient.GetQuery(ctx2, job.QueryId)
		if err != nil {
			s.logger.Error("Get Policy Error", zap.Error(err))
		}
		controlQuery, err := s.complianceClient.GetControlDetails(ctx2, job.QueryId)
		if err != nil {
			s.logger.Error("Get Control Error", zap.Error(err))
		}
		var query string
		var parameters []coreApi.QueryParameter
		if namedQuery != nil {
			query = namedQuery.Query.QueryToExecute
			parameters = namedQuery.Query.Parameters
		} else if controlQuery != nil {
			query = controlQuery.Policy.Definition
			for _, qp := range controlQuery.ParameterValues {
				parameters = append(parameters, coreApi.QueryParameter{
					Key: qp.Key,
				})
			}
		} else {
			_ = s.db.UpdateQueryRunnerJobStatus(job.ID, queryrunner.QueryRunnerFailed, "query ID not found")
			continue
		}
		s.logger.Info("Policy Runner publisher", zap.String("query", query))

		queryParams, err := s.coreClient.ListQueryParameters(&httpclient.Context{UserRole: api.AdminRole}, coreApi.ListQueryParametersRequest{})
		if err != nil {
			_ = s.db.UpdateQueryRunnerJobStatus(job.ID, queryrunner.QueryRunnerFailed, fmt.Sprintf("failed to list parameters: %s", err.Error()))
			return err
		}
		queryParamMap := make(map[string]string)
		for _, qp := range queryParams.Items {
			queryParamMap[qp.Key] = qp.Value
		}
		queryTemplate, err := template.New("query").Parse(query)
		if err != nil {
			return err
		}
		var queryOutput bytes.Buffer
		if err := queryTemplate.Execute(&queryOutput, queryParamMap); err != nil {
			_ = s.db.UpdateQueryRunnerJobStatus(job.ID, queryrunner.QueryRunnerFailed, fmt.Sprintf("failed to execute query template: %s", err.Error()))
			return fmt.Errorf("failed to execute query template: %w", err)
		}

		runnerJobMsg := queryrunner.Job{
			ID:          job.ID,
			RetryCount:  0,
			CreatedBy:   job.CreatedBy,
			TriggeredAt: job.CreatedAt.UnixMilli(),
			QueryId:     job.QueryId,
			Query:       queryOutput.String(),
		}

		jobJson, err := json.Marshal(runnerJobMsg)
		if err != nil {
			_ = s.db.UpdateQueryRunnerJobStatus(job.ID, queryrunner.QueryRunnerFailed, "failed to marshal job")
			s.logger.Error("failed to marshal Policy Runner Job", zap.Error(err), zap.Uint("runnerId", job.ID))
			continue
		}

		s.logger.Info("publishing query runner job", zap.Uint("jobId", job.ID))
		topic := queryrunner.JobQueueTopic
		seqNum, err := s.jq.Produce(ctx, topic, jobJson, fmt.Sprintf("job-%d-%d", job.ID, job.RetryCount))
		if err != nil {
			if err.Error() == "nats: no response from stream" {
				err = s.runSetupNatsStreams(ctx)
				if err != nil {
					s.logger.Error("Failed to setup nats streams", zap.Error(err))
					return err
				}
				seqNum, err = s.jq.Produce(ctx, topic, jobJson, fmt.Sprintf("job-%d-%d", job.ID, job.RetryCount))
				if err != nil {
					_ = s.db.UpdateQueryRunnerJobStatus(job.ID, queryrunner.QueryRunnerFailed, err.Error())
					s.logger.Error("failed to send job", zap.Error(err), zap.Uint("runnerId", job.ID))
					continue
				}
			} else {
				_ = s.db.UpdateQueryRunnerJobStatus(job.ID, queryrunner.QueryRunnerFailed, err.Error())
				s.logger.Error("failed to send query runner job", zap.Error(err), zap.Uint("runnerId", job.ID), zap.String("error message", err.Error()))
				continue
			}
		}

		if seqNum != nil {
			_ = s.db.UpdateQueryRunnerJobNatsSeqNum(job.ID, *seqNum)
		}
		_ = s.db.UpdateQueryRunnerJobStatus(job.ID, queryrunner.QueryRunnerQueued, "")
	}
	return nil
}
