package api

import (
	"github.com/labstack/echo/v4"
	"github.com/opengovern/og-util/pkg/config"
	"github.com/opengovern/og-util/pkg/opengovernance-es-sdk"
	"github.com/opengovern/og-util/pkg/steampipe"
	"github.com/opengovern/og-util/pkg/ticker"
	"github.com/opengovern/og-util/pkg/vault"
	"github.com/opengovern/opensecurity/pkg/utils"
	coreClient "github.com/opengovern/opensecurity/services/core/client"
	"github.com/opengovern/opensecurity/services/integration/api/credentials"
	integration_type2 "github.com/opengovern/opensecurity/services/integration/api/integration-types"
	"github.com/opengovern/opensecurity/services/integration/api/integrations"
	"github.com/opengovern/opensecurity/services/integration/db"
	integration_type "github.com/opengovern/opensecurity/services/integration/integration-type"
	"go.uber.org/zap"
	"golang.org/x/net/context"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"time"
)

type API struct {
	logger          *zap.Logger
	database        db.Database
	elastic         opengovernance.Client
	elasticConfig   config.ElasticSearch
	kubeClient      client.Client
	typeManager     *integration_type.IntegrationTypeManager
	vaultKeyId      string
	masterAccessKey string
	masterSecretKey string
	vault           vault.VaultSourceConfig

	steampipeOption *steampipe.Option

	coreClient coreClient.CoreServiceClient
}

func New(
	logger *zap.Logger,
	db db.Database,
	vault vault.VaultSourceConfig,
	steampipeOption *steampipe.Option,
	kubeClient client.Client,
	typeManager *integration_type.IntegrationTypeManager,
	elastic opengovernance.Client,
	coreClient coreClient.CoreServiceClient,
	elasticConfig config.ElasticSearch,
) *API {
	return &API{
		logger:          logger.Named("api"),
		database:        db,
		vault:           vault,
		steampipeOption: steampipeOption,
		kubeClient:      kubeClient,
		typeManager:     typeManager,
		elastic:         elastic,
		elasticConfig:   elasticConfig,
		coreClient:      coreClient,
	}
}

func (api *API) Register(e *echo.Echo) {
	integrationsApi := integrations.New(api.vault, api.database, api.logger, api.steampipeOption, api.kubeClient, api.typeManager)
	cred := credentials.New(api.vault, api.database, api.logger)
	integrationType := integration_type2.New(api.typeManager, api.database, api.logger, api.elastic, api.coreClient, api.elasticConfig)

	integrationsApi.Register(e.Group("/api/v1/integrations"))
	cred.Register(e.Group("/api/v1/credentials"))
	integrationType.Register(e.Group("/api/v1/integration-types"))

	utils.EnsureRunGoroutine(func() {
		api.CheckPluginInstallTimeout(context.Background())
	})
}

func (api *API) CheckPluginInstallTimeout(ctx context.Context) {
	t := ticker.NewTicker(time.Second*30, time.Second*10)
	defer t.Stop()
	for {
		select {
		case <-t.C:
			err := api.database.UpdatePluginInstallTimedOut(2)
			if err != nil {
				api.logger.Warn("failed to update plugin install timed out", zap.Error(err))
			}
		case <-ctx.Done():
			return
		}
	}
}
