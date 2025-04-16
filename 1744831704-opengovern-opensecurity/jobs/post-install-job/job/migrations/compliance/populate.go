package compliance

import (
	"context"
	"fmt"
	"github.com/opengovern/og-util/pkg/postgres"
	"github.com/opengovern/opensecurity/jobs/post-install-job/config"
	"github.com/opengovern/opensecurity/services/compliance/db"
	"go.uber.org/zap"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type Migration struct {
}

func (m Migration) IsGitBased() bool {
	return true
}

func (m Migration) AttachmentFolderPath() string {
	return ""
}

func (m Migration) Run(ctx context.Context, conf config.MigratorConfig, logger *zap.Logger) error {
	orm, err := postgres.NewClient(&postgres.Config{
		Host:    conf.PostgreSQL.Host,
		Port:    conf.PostgreSQL.Port,
		User:    conf.PostgreSQL.Username,
		Passwd:  conf.PostgreSQL.Password,
		DB:      "compliance",
		SSLMode: conf.PostgreSQL.SSLMode,
	}, logger)
	if err != nil {
		return fmt.Errorf("new postgres client: %w", err)
	}
	dbm := db.Database{Orm: orm}

	ormCore, err := postgres.NewClient(&postgres.Config{
		Host:    conf.PostgreSQL.Host,
		Port:    conf.PostgreSQL.Port,
		User:    conf.PostgreSQL.Username,
		Passwd:  conf.PostgreSQL.Password,
		DB:      "core",
		SSLMode: conf.PostgreSQL.SSLMode,
	}, logger)
	if err != nil {
		return fmt.Errorf("new postgres client: %w", err)
	}
	dbCore := db.Database{Orm: ormCore}

	p := GitParser{
		logger:             logger,
		frameworksChildren: make(map[string][]string),
		frameworksControls: make(map[string][]string),
		controlsPolicies:   make(map[string]db.Policy),
		benchmarks:         make(map[string]*db.Benchmark),
	}
	if err := p.ExtractCompliance(config.ComplianceGitPath, config.ControlEnrichmentGitPath); err != nil {
		logger.Error("failed to extract controls and benchmarks", zap.Error(err))
		return err
	}

	logger.Info("extracted controls, benchmarks and query views", zap.Int("controls", len(p.controls)), zap.Int("benchmarks", len(p.benchmarks)), zap.Int("query_views", len(p.policies)))

	loadedQueries := make(map[string]bool)
	err = dbm.Orm.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		tx.Model(&db.BenchmarkChild{}).Where("1=1").Unscoped().Delete(&db.BenchmarkChild{})
		tx.Model(&db.BenchmarkControls{}).Where("1=1").Unscoped().Delete(&db.BenchmarkControls{})
		tx.Model(&db.Benchmark{}).Where("1=1").Unscoped().Delete(&db.Benchmark{})
		tx.Model(&db.Control{}).Where("1=1").Unscoped().Delete(&db.Control{})
		tx.Model(&db.PolicyParameter{}).Where("1=1").Unscoped().Delete(&db.PolicyParameter{})
		tx.Model(&db.Policy{}).Where("1=1").Unscoped().Delete(&db.Policy{})

		for _, obj := range p.policies {
			obj.Controls = nil
			err := tx.Clauses(clause.OnConflict{
				Columns:   []clause.Column{{Name: "id"}}, // key column
				DoNothing: true,
			}).Create(&obj).Error
			if err != nil {
				return err
			}
			for _, param := range obj.Parameters {
				err = tx.Clauses(clause.OnConflict{
					Columns:   []clause.Column{{Name: "key"}, {Name: "policy_id"}}, // key columns
					DoNothing: true,
				}).Create(&param).Error
				if err != nil {
					return fmt.Errorf("failure in query parameter insert: %v", err)
				}
			}
			loadedQueries[obj.ID] = true
		}
		return nil
	})
	if err != nil {
		logger.Error("failed to insert policies", zap.Error(err))
		return err
	}

	err = dbCore.Orm.WithContext(ctx).Transaction(func(tx *gorm.DB) error {
		for _, obj := range p.policyParamValues {
			err := tx.Clauses(clause.OnConflict{
				Columns: []clause.Column{{Name: "key"}, {Name: "control_id"}},
				DoUpdates: clause.Assignments(map[string]interface{}{
					"value": gorm.Expr("CASE WHEN policy_parameter_values.value = '' THEN ? ELSE policy_parameter_values.value END", obj.Value),
				}),
			}).Create(&obj).Error
			if err != nil {
				return err
			}
		}
		return nil
	})
	if err != nil {
		logger.Error("failed to insert query params", zap.Error(err))
		return err
	}

	missingQueries := make(map[string]bool)
	err = dbm.Orm.WithContext(ctx).Transaction(func(tx *gorm.DB) error {

		for _, obj := range p.controls {
			obj.Benchmarks = nil
			if obj.PolicyID != nil && !loadedQueries[*obj.PolicyID] {
				missingQueries[*obj.PolicyID] = true
				logger.Info("query not found", zap.String("query_id", *obj.PolicyID))
				continue
			}
			err := tx.Clauses(clause.OnConflict{
				Columns:   []clause.Column{{Name: "id"}},
				DoNothing: true,
			}).Create(&obj).Error
			if err != nil {
				return err
			}
			for _, tag := range obj.Tags {
				err = tx.Clauses(clause.OnConflict{
					Columns:   []clause.Column{{Name: "key"}, {Name: "control_id"}}, // key columns
					DoNothing: true,
				}).Create(&tag).Error
				if err != nil {
					return fmt.Errorf("failure in control tag insert: %v", err)
				}
			}
		}

		for _, obj := range p.benchmarks {
			obj.Children = nil
			obj.Controls = nil
			err := tx.Clauses(clause.OnConflict{
				Columns:   []clause.Column{{Name: "id"}}, // key column
				DoNothing: true,
			}).Create(&obj).Error
			if err != nil {
				return err
			}
			for _, tag := range obj.Tags {
				err = tx.Clauses(clause.OnConflict{
					Columns:   []clause.Column{{Name: "key"}, {Name: "benchmark_id"}}, // key columns
					DoNothing: true,
				}).Create(&tag).Error
				if err != nil {
					return fmt.Errorf("failure in benchmark tag insert: %v", err)
				}
			}
		}

		for _, obj := range p.benchmarks {
			for _, child := range p.frameworksChildren[obj.ID] {
				err := tx.Clauses(clause.OnConflict{
					DoNothing: true,
				}).Create(&db.BenchmarkChild{
					BenchmarkID: obj.ID,
					ChildID:     child,
				}).Error
				if err != nil {
					logger.Error("inserted controls and benchmarks", zap.Error(err))
					return err
				}
			}

			for _, control := range p.frameworksControls[obj.ID] {
				err := tx.Clauses(clause.OnConflict{
					DoNothing: true,
				}).Create(&db.BenchmarkControls{
					BenchmarkID: obj.ID,
					ControlID:   control,
				}).Error
				if err != nil {
					logger.Info("inserted controls and benchmarks", zap.Error(err))
					return err
				}
			}
		}

		missingQueriesList := make([]string, 0, len(missingQueries))
		for query := range missingQueries {
			missingQueriesList = append(missingQueriesList, query)
		}
		if len(missingQueriesList) > 0 {
			logger.Warn("missing policies", zap.Strings("policies", missingQueriesList))
		}
		return nil
	})

	if err != nil {
		logger.Info("inserted controls and benchmarks", zap.Error(err))
		return err
	}
	return nil
}
