package compliance_quick_run

import (
	"fmt"
	api2 "github.com/opengovern/og-util/pkg/api"
	"github.com/opengovern/og-util/pkg/httpclient"
	"github.com/opengovern/opensecurity/services/compliance/api"
	coreApi "github.com/opengovern/opensecurity/services/core/api"
	"github.com/opengovern/opensecurity/services/scheduler/db/model"
	"go.uber.org/zap"
)

func (s *JobScheduler) validateComplianceJob(framework api.Benchmark) error {

	//err := s.tableValidation(framework)
	//if err != nil {
	//	return err
	//}

	listOfParameters, err := s.getParametersUnderFramework(framework, make(map[string]FrameworkParametersCache))
	if err != nil {
		return err
	}

	queryParams, err := s.coreClient.ListQueryParameters(&httpclient.Context{UserRole: api2.AdminRole}, coreApi.ListQueryParametersRequest{})
	if err != nil {
		s.logger.Error("failed to get query parameters", zap.Error(err))
		return err
	}
	queryParamMap := make(map[string]string)
	for _, qp := range queryParams.Items {
		if qp.Value != "" {
			queryParamMap[qp.Key] = qp.Value
		}
	}

	for param := range listOfParameters {
		if _, ok := queryParamMap[param]; !ok {
			return fmt.Errorf("query parameter %s not exists", param)
		}
	}
	return nil
}

func (s *JobScheduler) tableValidation(framework api.Benchmark) error {
	validation, err := s.db.GetFrameworkValidation(framework.ID)
	if err != nil {
		s.logger.Error("failed to get validation", zap.Error(err))
		return err
	}
	if validation == nil {
		s.logger.Info("getting framework tables")
		listOfTables, err := s.getTablesUnderBenchmark(framework)
		if err != nil {
			_ = s.db.CreateFrameworkValidation(&model.FrameworkValidation{
				FrameworkID:    framework.ID,
				FailureMessage: err.Error(),
			})
			return err
		}

		integrationTypes, err := s.integrationClient.ListIntegrationTypes(&httpclient.Context{UserRole: api2.AdminRole})
		if err != nil {
			_ = s.db.CreateFrameworkValidation(&model.FrameworkValidation{
				FrameworkID:    framework.ID,
				FailureMessage: err.Error(),
			})
			return err
		}
		integrationTypesMap := make(map[string]bool)
		tablesMap := make(map[string]struct{})
		for _, it := range integrationTypes {
			integrationTypesMap[it] = true
			tables, err := s.integrationClient.GetIntegrationTypeTables(&httpclient.Context{UserRole: api2.AdminRole}, it)
			if err != nil {
				_ = s.db.CreateFrameworkValidation(&model.FrameworkValidation{
					FrameworkID:    framework.ID,
					FailureMessage: err.Error(),
				})
				return err
			}
			for table, _ := range tables {
				tablesMap[table] = struct{}{}
			}
		}

		s.logger.Info("getting integration types")
		for _, itName := range framework.IntegrationTypes {
			if _, ok := integrationTypesMap[itName]; !ok {
				_ = s.db.CreateFrameworkValidation(&model.FrameworkValidation{
					FrameworkID:    framework.ID,
					FailureMessage: fmt.Errorf("integration type not valid: %s", itName).Error(),
				})
				return fmt.Errorf("integration type not valid: %s", itName)
			}
		}

		s.logger.Info("checking tables")
		for table := range listOfTables {
			if _, ok := tablesMap[table]; !ok {
				_ = s.db.CreateFrameworkValidation(&model.FrameworkValidation{
					FrameworkID:    framework.ID,
					FailureMessage: fmt.Sprintf("table %s not exist", table),
				})
				return fmt.Errorf("table %s not exist", table)
			}
		}

		s.logger.Info("creating framework validation")
		_ = s.db.CreateFrameworkValidation(&model.FrameworkValidation{
			FrameworkID:    framework.ID,
			FailureMessage: "",
		})
	} else if validation.FailureMessage != "" {
		return fmt.Errorf("framework %s has failed validation: %s", framework.ID, validation.FailureMessage)
	}
	return nil
}

type FrameworkParametersCache struct {
	ListParameters map[string]bool
}

// getTablesUnderBenchmark ctx context.Context, benchmarkId string -> primaryTables, listOfTables, error
func (s *JobScheduler) getTablesUnderBenchmark(framework api.Benchmark) (map[string]bool, error) {
	ctx := &httpclient.Context{UserRole: api2.AdminRole}
	listOfTables := make(map[string]bool)

	s.logger.Info("getting framework controls")
	controlIDsMap, err := s.getControlsUnderBenchmark(framework)
	if err != nil {
		s.logger.Error("failed to fetch controls", zap.Error(err))
		return nil, err
	}
	var controlIDs []string
	for controlID := range controlIDsMap {
		controlIDs = append(controlIDs, controlID)
	}

	s.logger.Info("listing getting controls", zap.Strings("controlIDs", controlIDs))
	controls, err := s.complianceClient.ListControl(ctx, controlIDs, nil)
	if err != nil {
		s.logger.Error("failed to fetch controls", zap.Error(err))
		return nil, err
	}

	s.logger.Info("getting controls resources")
	for _, c := range controls {
		if c.Policy != nil {
			for _, t := range c.Policy.ListOfResources {
				if t == "" {
					continue
				}
				listOfTables[t] = true
			}
		}
	}

	return listOfTables, nil
}

func (s *JobScheduler) getControlsUnderBenchmark(framework api.Benchmark) (map[string]bool, error) {
	ctx := &httpclient.Context{UserRole: api2.AdminRole}

	s.logger.Info("getting framework children", zap.String("framework_id", framework.ID), zap.Strings("children", framework.Children))

	controls := make(map[string]bool)
	for _, c := range framework.Controls {
		controls[c] = true
	}
	if len(framework.Children) > 0 {
		children, err := s.complianceClient.ListBenchmarks(ctx, framework.Children, nil)
		if err != nil {
			s.logger.Error("failed to fetch children", zap.Error(err))
			return nil, err
		}
		for _, child := range children {
			childControls, err := s.getControlsUnderBenchmark(child)
			if err != nil {
				s.logger.Error("failed to fetch controls", zap.Error(err))
				return nil, err
			}
			for k, _ := range childControls {
				controls[k] = true
			}
		}
	}

	s.logger.Info("got framework controls", zap.Any("controls", controls))
	return controls, nil
}

// getParametersUnderFramework ctx context.Context, benchmarkId string -> primaryTables, listOfTables, error
func (s *JobScheduler) getParametersUnderFramework(framework api.Benchmark, frameworkCache map[string]FrameworkParametersCache) (map[string]bool, error) {
	listOfParameters := make(map[string]bool)

	controls, err := s.complianceClient.ListControl(&httpclient.Context{UserRole: api2.AdminRole}, framework.Controls, nil)
	if err != nil {
		s.logger.Error("failed to fetch controls", zap.Error(err))
		return nil, err
	}
	for _, c := range controls {
		if c.Policy != nil {
			for _, t := range c.Policy.Parameters {
				listOfParameters[t.Key] = true
			}
		}
	}

	children, err := s.complianceClient.ListBenchmarks(&httpclient.Context{UserRole: api2.AdminRole}, framework.Children, nil)
	if err != nil {
		s.logger.Error("failed to fetch children", zap.Error(err))
		return nil, err
	}
	for _, child := range children {
		var childListOfParameters map[string]bool
		if cache, ok := frameworkCache[child.ID]; ok {
			childListOfParameters = cache.ListParameters
		} else {
			childListOfParameters, err = s.getParametersUnderFramework(child, frameworkCache)
			if err != nil {
				return nil, err
			}
			frameworkCache[child.ID] = FrameworkParametersCache{
				ListParameters: childListOfParameters,
			}
		}

		for k, _ := range childListOfParameters {
			childListOfParameters[k] = true
		}
	}
	return listOfParameters, nil
}
