package integrations

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/goccy/go-yaml"
	"github.com/google/uuid"
	"github.com/jackc/pgtype"
	kedav1alpha1 "github.com/kedacore/keda/v2/apis/keda/v1alpha1"
	"github.com/labstack/echo/v4"
	"github.com/opengovern/og-util/pkg/api"
	"github.com/opengovern/og-util/pkg/httpserver"
	"github.com/opengovern/og-util/pkg/integration"
	"github.com/opengovern/og-util/pkg/steampipe"
	"github.com/opengovern/og-util/pkg/vault"
	"github.com/opengovern/opensecurity/pkg/utils"
	"github.com/opengovern/opensecurity/services/integration/api/models"
	"github.com/opengovern/opensecurity/services/integration/db"
	"github.com/opengovern/opensecurity/services/integration/entities"
	integration_type "github.com/opengovern/opensecurity/services/integration/integration-type"
	models2 "github.com/opengovern/opensecurity/services/integration/models"
	"go.uber.org/zap"
	"golang.org/x/net/context"
	appsv1 "k8s.io/api/apps/v1"
	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

type API struct {
	vault        vault.VaultSourceConfig
	logger       *zap.Logger
	database     db.Database
	kubeClient   client.Client
	typesManager *integration_type.IntegrationTypeManager

	steampipeOption *steampipe.Option
	steampipeLock   sync.Mutex
	steampipeConn   *steampipe.Database
}

const (
	TemplateDeploymentPath          string = "/integrations/deployment-template.yaml"
	TemplateManualsDeploymentPath   string = "/integrations/deployment-template-manuals.yaml"
	TemplateScaledObjectPath        string = "/integrations/scaled-object-template.yaml"
	TemplateManualsScaledObjectPath string = "/integrations/scaled-object-template-manuals.yaml"
)

func New(
	vault vault.VaultSourceConfig,
	database db.Database,
	logger *zap.Logger,
	steampipeOption *steampipe.Option,
	kubeClien client.Client,
	typesManager *integration_type.IntegrationTypeManager,
) API {
	return API{
		vault:           vault,
		database:        database,
		logger:          logger.Named("integrations"),
		steampipeOption: steampipeOption,
		steampipeLock:   sync.Mutex{},
		kubeClient:      kubeClien,
		typesManager:    typesManager,
	}
}

func (h *API) Register(g *echo.Group) {
	g.GET("", httpserver.AuthorizeHandler(h.List, api.ViewerRole))
	g.POST("/list", httpserver.AuthorizeHandler(h.ListByFilters, api.ViewerRole))
	g.POST("/discover", httpserver.AuthorizeHandler(h.DiscoverIntegrations, api.EditorRole))
	g.POST("/add", httpserver.AuthorizeHandler(h.AddIntegrations, api.EditorRole))
	g.PUT("/:IntegrationID/healthcheck", httpserver.AuthorizeHandler(h.IntegrationHealthcheck, api.EditorRole))
	g.DELETE("/:IntegrationID", httpserver.AuthorizeHandler(h.Delete, api.EditorRole))
	g.GET("/:IntegrationID", httpserver.AuthorizeHandler(h.Get, api.ViewerRole))
	g.POST("/:IntegrationID", httpserver.AuthorizeHandler(h.Update, api.EditorRole))
	g.GET("/integration-groups", httpserver.AuthorizeHandler(h.ListIntegrationGroups, api.ViewerRole))
	g.GET("/integration-groups/:integrationGroupName", httpserver.AuthorizeHandler(h.GetIntegrationGroup, api.ViewerRole))
	g.PUT("/sample/purge", httpserver.AuthorizeHandler(h.PurgeSampleData, api.EditorRole))
	g.PUT("/:integration_id/resource", httpserver.AuthorizeHandler(h.SetResourceTypesForIntegration, api.EditorRole))

	types := g.Group("/types")
	types.GET("", httpserver.AuthorizeHandler(h.ListIntegrationTypes, api.ViewerRole))
	types.GET("/:integrationTypeId", httpserver.AuthorizeHandler(h.GetIntegrationType, api.ViewerRole))
	types.GET("/:integrationTypeId/ui/spec", httpserver.AuthorizeHandler(h.GetIntegrationTypeUiSpec, api.ViewerRole))
	types.PUT("/:integration_type/enable", httpserver.AuthorizeHandler(h.EnableIntegrationType, api.EditorRole))
	types.PUT("/:integration_type/disable", httpserver.AuthorizeHandler(h.DisableIntegrationType, api.EditorRole))
	types.PUT("/:integration_type/upgrade", httpserver.AuthorizeHandler(h.UpgradeIntegrationType, api.EditorRole))

	resourceTypes := types.Group("/:integration_type/resource_types")
	resourceTypes.GET("", httpserver.AuthorizeHandler(h.ListIntegrationTypeResourceTypes, api.ViewerRole))
	resourceTypes.GET("/:resource_type", httpserver.AuthorizeHandler(h.GetIntegrationTypeResourceType, api.ViewerRole))
}

func (h *API) getSteampipeConn() (*steampipe.Database, error) {
	if h.steampipeConn == nil {
		h.steampipeLock.Lock()
		defer h.steampipeLock.Unlock()
		if h.steampipeConn == nil {
			steampipeConn, err := steampipe.NewSteampipeDatabase(*h.steampipeOption)
			if err != nil {
				h.logger.Error("failed to create steampipe connection", zap.Error(err))
				return nil, err
			}
			h.steampipeConn = steampipeConn
		}
	}
	return h.steampipeConn, nil
}

// DiscoverIntegrations godoc
//
//	@Summary		Discover integrations
//	@Description	Discover integrations and return back the list of integrations and credential ID
//	@Security		BearerToken
//	@Tags			integrations
//	@Produce		json
//	@Success		200
//	@Param			request	body	models.DiscoverIntegrationRequest	true	"Request"
//	@Router			/integration/api/v1/integrations/discover [post]
func (h *API) DiscoverIntegrations(c echo.Context) error {
	var req models.DiscoverIntegrationRequest

	contentType := c.Request().Header.Get("Content-Type")
	if strings.HasPrefix(contentType, "multipart/form-data") {
		h.logger.Info("file imported")
		err := c.Request().ParseMultipartForm(10 << 20) // 10 MB max memory
		if err != nil {
			return echo.NewHTTPError(http.StatusBadRequest, "Failed to parse multipart form")
		}

		formData := make(map[string]any)

		for key, values := range c.Request().MultipartForm.Value {
			if len(values) > 0 {
				if key == "integrationType" || key == "integration_type" {
					req.IntegrationType = h.typesManager.ParseType(values[0])
				} else if key == "credentialType" || key == "credential_type" {
					req.CredentialType = values[0]

				} else if key == "description" || key == "Description" {
					req.Description = values[0]
				} else {
					keys := strings.Split(key, ".")
					formData[keys[1]] = values[0]
				}
			}
		}

		for key, fileHeaders := range c.Request().MultipartForm.File {
			if len(fileHeaders) > 0 {
				file, err := fileHeaders[0].Open()
				if err != nil {
					return echo.NewHTTPError(http.StatusInternalServerError, "Failed to open uploaded file")
				}
				defer file.Close()

				content, err := ioutil.ReadAll(file)
				if err != nil {
					return echo.NewHTTPError(http.StatusInternalServerError, "Failed to read uploaded file")
				}
				keys := strings.Split(key, ".")
				formData[keys[1]] = string(content)
			}
		}
		req.Credentials = formData
	} else {
		if err := c.Bind(&req); err != nil {
			return echo.NewHTTPError(http.StatusBadRequest, "invalid request")
		}
	}

	var jsonData []byte
	var err error
	var integrationType integration.Type
	var credentialIDStr string

	if req.CredentialID != nil {
		credentialIDStr = *req.CredentialID
		credential, err := h.database.GetCredential(*req.CredentialID)
		if err != nil {
			h.logger.Error("failed to get credential", zap.Error(err))
			return echo.NewHTTPError(http.StatusNotFound, "credential not found")
		}
		integrationType = credential.IntegrationType

		mapData, err := h.vault.Decrypt(c.Request().Context(), credential.Secret)
		if err != nil {
			h.logger.Error("failed to decrypt secret", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to decrypt config")
		}

		if _, ok := h.typesManager.GetIntegrationTypeMap()[req.IntegrationType]; !ok {
			return echo.NewHTTPError(http.StatusBadRequest, "invalid integration type")
		}

		jsonData, err = json.Marshal(mapData)
		if err != nil {
			h.logger.Error("failed to marshal json data", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to marshal json data")
		}
	} else {
		integrationType = req.IntegrationType
		jsonData, err = json.Marshal(req.Credentials)
		if err != nil {
			h.logger.Error("failed to marshal json data", zap.Error(err))
			return echo.NewHTTPError(http.StatusBadRequest, "failed to marshal json data")
		}
		var mapData map[string]any
		err = json.Unmarshal(jsonData, &mapData)
		if err != nil {
			h.logger.Error("failed to unmarshal json data", zap.Error(err))
		}
		secret, err := h.vault.Encrypt(c.Request().Context(), mapData)
		if err != nil {
			h.logger.Error("failed to encrypt secret", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to encrypt config")
		}
		masked := make(map[string]any)
		for key, value := range req.Credentials {
			strValue, ok := value.(string) // Ensure the value is a string
			if !ok {
				// If it's not a string, just skip masking
				masked[key] = "not available"
				continue
			}

			// Get the last 5 characters, or the full string if it's shorter
			if len(strValue) > 5 {
				masked[key] = "*****" + strValue[len(strValue)-5:]
			} else {
				masked[key] = "*****" + strValue
			}
		}
		// convert to jsonb
		maskedSecreyJsonData, err := json.Marshal(masked)
		maskedSecretJsonb := pgtype.JSONB{}
		err = maskedSecretJsonb.Set(maskedSecreyJsonData)
		if err != nil {
			h.logger.Error("failed to set masked secret", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to set masked secret")
		}

		credentialID := uuid.New()

		metadata := make(map[string]string)
		metadataJsonData, err := json.Marshal(metadata)
		credentialMetadataJsonb := pgtype.JSONB{}

		err = credentialMetadataJsonb.Set(metadataJsonData)
		err = h.database.CreateCredential(&models2.Credential{
			ID:              credentialID,
			IntegrationType: req.IntegrationType,
			CredentialType:  req.CredentialType,
			Description:     req.Description,
			MaskedSecret:    maskedSecretJsonb,
			Secret:          secret,
			Metadata:        credentialMetadataJsonb,
		})
		if err != nil {
			h.logger.Error("failed to create credential", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to create credential")
		}
		credentialIDStr = credentialID.String()
	}

	integration, ok := h.typesManager.GetIntegrationTypeMap()[integrationType]
	if !ok {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid integrationType")
	}

	if integration == nil {
		return echo.NewHTTPError(http.StatusBadRequest, "failed to marshal json data")
	}

	plugin, err := h.database.GetPluginByID(integrationType.String())
	if err != nil {
		h.logger.Error("failed to get plugin", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get integration setup")
	}
	if plugin.OperationalStatus != models2.IntegrationPluginOperationalStatusEnabled ||
		plugin.InstallState == models2.IntegrationTypeInstallStateNotInstalled {
		return echo.NewHTTPError(http.StatusBadRequest, "integration type is not enabled")
	}

	integrations, err := integration.DiscoverIntegrations(jsonData)
	h.logger.Info("discovered integrations", zap.Any("integrations", integrations))
	var integrationsAPI []models.Integration
	for _, in := range integrations {
		i := models2.Integration{Integration: in}
		integrationAPI, err := i.ToApi()
		if err != nil {
			h.logger.Error("failed to create integration api", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to create integration api")
		}

		healthy, err := integration.HealthCheck(jsonData, integrationAPI.ProviderID, integrationAPI.Labels, integrationAPI.Annotations)
		if err != nil || !healthy {
			h.logger.Info("integration is not healthy", zap.String("integration_id", i.IntegrationID.String()), zap.Error(err))
			integrationAPI.State = models.IntegrationStateInactive
		} else {
			integrationAPI.State = models.IntegrationStateActive
		}

		integrationsAPI = append(integrationsAPI, *integrationAPI)
	}

	return c.JSON(http.StatusOK, models.DiscoverIntegrationResponse{
		CredentialID: credentialIDStr,
		Integrations: integrationsAPI,
	})
}

// AddIntegrations godoc
//
//	@Summary		Add integrations
//	@Description	Add integrations by given credential ID and integration IDs
//	@Security		BearerToken
//	@Tags			integrations
//	@Produce		json
//	@Success		200
//	@Param			request	body	models.AddIntegrationsRequest	true	"Request"
//	@Router			/integration/api/v1/integrations/add [post]
func (h *API) AddIntegrations(c echo.Context) error {
	var req models.AddIntegrationsRequest

	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid request")
	}

	credentialID, err := uuid.Parse(req.CredentialID)
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid credential id")
	}
	credential, err := h.database.GetCredential(req.CredentialID)
	if err != nil {
		h.logger.Error("failed to get credential", zap.Error(err))
		return echo.NewHTTPError(http.StatusNotFound, "credential not found")
	}

	mapData, err := h.vault.Decrypt(c.Request().Context(), credential.Secret)
	if err != nil {
		h.logger.Error("failed to decrypt secret", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to decrypt config")
	}

	if _, ok := h.typesManager.GetIntegrationTypeMap()[req.IntegrationType]; !ok {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid integration type")
	}

	plugin, err := h.database.GetPluginByID(req.IntegrationType.String())
	if err != nil {
		h.logger.Error("failed to get plugin", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get integration setup")
	}
	if plugin.OperationalStatus != models2.IntegrationPluginOperationalStatusEnabled ||
		plugin.InstallState == models2.IntegrationTypeInstallStateNotInstalled {
		return echo.NewHTTPError(http.StatusBadRequest, "integration type is not enabled")
	}

	jsonData, err := json.Marshal(mapData)
	if err != nil {
		h.logger.Error("failed to marshal json data", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to marshal json data")
	}

	integrationType := h.typesManager.GetIntegrationTypeMap()[req.IntegrationType]
	if integrationType == nil {
		return echo.NewHTTPError(http.StatusBadRequest, "failed to marshal json data")
	}

	integrations, err := integrationType.DiscoverIntegrations(jsonData)
	if err != nil {
		h.logger.Error("failed to create credential", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to create credential")
	}

	integrationTypeIntegrations, err := h.database.ListIntegration([]integration.Type{req.IntegrationType})

	providerIDs := make(map[string]bool)
	for _, i := range req.ProviderIDs {
		providerIDs[i] = true
	}
	integrationTypeIntegrationsMap := make(map[string]bool)
	for _, i := range integrationTypeIntegrations {
		integrationTypeIntegrationsMap[i.ProviderID] = true
	}
	//
	var count = 0

	for _, in := range integrations {
		i := models2.Integration{Integration: in}
		if _, ok := providerIDs[i.ProviderID]; !ok {
			continue
		}
		if _, ok := integrationTypeIntegrationsMap[i.ProviderID]; ok {
			continue
		}
		i.IntegrationType = req.IntegrationType

		i.CredentialID = credentialID

		healthcheckTime := time.Now()
		i.LastCheck = &healthcheckTime

		if i.Labels.Status != pgtype.Present {
			err = i.Labels.Set("{}")
			if err != nil {
				h.logger.Error("failed to set label", zap.Error(err))
				return echo.NewHTTPError(http.StatusInternalServerError, "failed to set label")
			}
		}

		if i.Annotations.Status != pgtype.Present {
			err = i.Annotations.Set("{}")
			if err != nil {
				h.logger.Error("failed to set annotations", zap.Error(err))
				return echo.NewHTTPError(http.StatusInternalServerError, "failed to set annotations")
			}
		}

		iApi, err := i.ToApi()
		if err != nil {
			h.logger.Error("failed to create integration api", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to create integration api")
		}
		healthy, err := integrationType.HealthCheck(jsonData, i.ProviderID, iApi.Labels, iApi.Annotations)
		if err != nil || !healthy {
			h.logger.Info("integration is not healthy", zap.String("integration_id", i.IntegrationID.String()), zap.Error(err))
			i.State = integration.IntegrationStateInactive
		} else {
			i.State = integration.IntegrationStateActive
		}

		err = h.database.CreateIntegration(&i)
		if err != nil {
			h.logger.Error("failed to create integration", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to create integration")
		}
		count++
		// update credentials
	}
	err = h.database.UpdateCredentialIntegrationCount(req.CredentialID, count)

	return c.NoContent(http.StatusOK)
}

// IntegrationHealthcheck godoc
//
//	@Summary		Add integrations
//	@Description	Add integrations by given credential ID and integration IDs
//	@Security		BearerToken
//	@Tags			integrations
//	@Produce		json
//	@Success		200
//	@Router			/integration/api/v1/integrations/{IntegrationID}/healthcheck [put]
func (h *API) IntegrationHealthcheck(c echo.Context) error {
	IntegrationID, err := uuid.Parse(c.Param("IntegrationID"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid request")
	}

	integ, err := h.database.GetIntegration(IntegrationID)
	if err != nil {
		h.logger.Error("failed to get integration", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get integration")
	}

	defer func() {
		if err != nil && integ != nil && integ.State != integration.IntegrationStateArchived {
			h.logger.Error("healthcheck failed", zap.Error(err))
			healthcheckTime := time.Now()
			integ.LastCheck = &healthcheckTime
			integ.State = integration.IntegrationStateInactive
			_, err = integ.AddAnnotations("platform/integration/health-reason", err.Error())
			if err != nil {
				h.logger.Error("failed to add annotations", zap.Error(err))
			}
			err = h.database.UpdateIntegration(integ)
			if err != nil {
				h.logger.Error("failed to update integration", zap.Error(err), zap.Any("integration", *integ))
			}
		}
	}()

	credential, err := h.database.GetCredential(integ.CredentialID.String())
	if err != nil {
		h.logger.Error("failed to get credential", zap.Error(err))
		return echo.NewHTTPError(http.StatusNotFound, "credential not found")
	}
	if credential == nil {
		h.logger.Error("credential not found", zap.Any("credentialId", integ.CredentialID))
		return echo.NewHTTPError(http.StatusNotFound, "credential not found")
	}

	mapData, err := h.vault.Decrypt(c.Request().Context(), credential.Secret)
	if err != nil {
		h.logger.Error("failed to decrypt secret", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to decrypt config")
	}

	if _, ok := h.typesManager.GetIntegrationTypeMap()[integ.IntegrationType]; !ok {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid integration type")
	}

	jsonData, err := json.Marshal(mapData)
	if err != nil {
		h.logger.Error("failed to marshal json data", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to marshal json data")
	}

	integrationType := h.typesManager.GetIntegrationTypeMap()[integ.IntegrationType]

	if integrationType == nil {
		return echo.NewHTTPError(http.StatusBadRequest, "failed to marshal json data")
	}
	integrationApi, err := integ.ToApi()
	if err != nil {
		h.logger.Error("failed to create integration api", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to create integration api")
	}

	healthy, err := integrationType.HealthCheck(jsonData, integrationApi.ProviderID, integrationApi.Labels, integrationApi.Annotations)
	if err != nil || !healthy {
		h.logger.Error("healthcheck failed", zap.Error(err))
		if integ.State != integration.IntegrationStateArchived {
			integ.State = integration.IntegrationStateInactive
		}
		_, err = integ.AddAnnotations("platform/integration/health-reason", err.Error())
		if err != nil {
			h.logger.Error("failed to add annotations", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to add annotations")
		}
	} else {
		if integ.State != integration.IntegrationStateArchived {
			integ.State = integration.IntegrationStateActive
		}
	}
	healthcheckTime := time.Now()
	integ.LastCheck = &healthcheckTime
	err = h.database.UpdateIntegration(integ)
	if err != nil {
		h.logger.Error("failed to update integration", zap.Error(err), zap.Any("integration", *integ))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to update integration")
	}

	integrationApi, err = integ.ToApi()
	if err != nil {
		h.logger.Error("failed to create integration api", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to create integration api")
	}

	return c.JSON(http.StatusOK, *integrationApi)
}

// Delete godoc
//
//	@Summary		Delete credential
//	@Description	Delete credential
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Success		200
//	@Param			IntegrationID	path	string	true	"IntegrationID"
//	@Router			/integration/api/v1/integrations/{IntegrationID} [delete]
func (h *API) Delete(c echo.Context) error {
	IntegrationID, err := uuid.Parse(c.Param("IntegrationID"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid request")
	}

	err = h.database.DeleteIntegration(IntegrationID)
	if err != nil {
		h.logger.Error("failed to delete credential", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to delete credential")
	}

	return c.NoContent(http.StatusOK)
}

// List godoc
//
//	@Summary		List integrations
//	@Description	List integrations
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Param			integration_type	query		[]string	false	"integration type filter"
//	@Success		200					{object}	models.ListIntegrationsResponse
//	@Router			/integration/api/v1/integrations [get]
func (h *API) List(c echo.Context) error {
	integrationTypesStr := httpserver.QueryArrayParam(c, "integration_type")

	var integrationTypes []integration.Type
	for _, i := range integrationTypesStr {
		integrationTypes = append(integrationTypes, integration.Type(i))
	}

	integrations, err := h.database.ListIntegration(integrationTypes)
	if err != nil {
		h.logger.Error("failed to list credentials", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to list credential")
	}

	var items []models.Integration
	for _, integration := range integrations {
		item, err := integration.ToApi()
		if err != nil {
			h.logger.Error("failed to convert integration to API model", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to convert integration to API model")
		}
		items = append(items, *item)
	}

	return c.JSON(http.StatusOK, models.ListIntegrationsResponse{
		Integrations: items,
		TotalCount:   len(items),
	})
}

// ListByFilters godoc
//
//	@Summary		List credentials with given filters
//	@Description	List credentials with given filters
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Success		200	{object}	models.ListIntegrationsResponse
//	@Router			/integration/api/v1/integrations/list [post]
func (h *API) ListByFilters(c echo.Context) error {
	var req models.ListIntegrationsRequest

	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid request")
	}

	integrations, err := h.database.ListIntegrationsByFilters(req.IntegrationID, req.IntegrationType, req.NameRegex, req.ProviderIDRegex)
	if err != nil {
		h.logger.Error("failed to list credentials", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to list credential")
	}

	var items []models.Integration
	for _, integration := range integrations {
		item, err := integration.ToApi()
		if err != nil {
			h.logger.Error("failed to convert integration to API model", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to convert integration to API model")
		}
		items = append(items, *item)
	}

	totalCount := len(items)
	sort.Slice(items, func(i, j int) bool {
		return items[i].Name < items[j].Name
	})
	if req.PerPage != nil {
		if req.Cursor == nil {
			items = utils.Paginate(1, *req.PerPage, items)
		} else {
			items = utils.Paginate(*req.Cursor, *req.PerPage, items)
		}
	}

	return c.JSON(http.StatusOK, models.ListIntegrationsResponse{
		Integrations: items,
		TotalCount:   totalCount,
	})
}

// ListIntegrationGroups godoc
//
//	@Summary		List integration groups and their integrations
//	@Description	List integration groups and their integrations
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Param			populateIntegrations	query		bool	false	"Populate connections"	default(false)
//	@Success		200						{object}	[]models.IntegrationGroup
//	@Router			/integration/api/v1/integrations/integration-groups [get]
func (h *API) ListIntegrationGroups(c echo.Context) error {
	populateIntegrations := false
	var err error
	if populateIntegrationsStr := c.QueryParam("populateIntegrations"); populateIntegrationsStr != "" {
		populateIntegrations, err = strconv.ParseBool(populateIntegrationsStr)
		if err != nil {
			return c.JSON(http.StatusBadRequest, "populateConnections is not a valid boolean")
		}
	}

	integrationGroups, err := h.database.ListIntegrationGroups()
	if err != nil {
		h.logger.Error("failed to list credentials", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to list credential")
	}

	steampipeConn, err := h.getSteampipeConn()
	if err != nil {
		h.logger.Error("failed to get steampipe connection", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get steampipe connection")
	}

	var items []models.IntegrationGroup
	for _, integrationGroup := range integrationGroups {
		integrationGroupApi, err := entities.NewIntegrationGroup(c.Request().Context(), steampipeConn, integrationGroup)
		if err != nil {
			h.logger.Error("failed to convert integration group to API model", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to convert integration group to API model")
		}
		if populateIntegrations {
			integrations, err := h.database.ListIntegrationsByFilters(integrationGroupApi.IntegrationIds, nil, nil, nil)
			if err != nil {
				h.logger.Error("failed to list integrations", zap.Error(err))
				return echo.NewHTTPError(http.StatusInternalServerError, "failed to list integrations")
			}
			var apiIntegrations []models.Integration
			for _, integration := range integrations {
				apiIntegration, err := integration.ToApi()
				if err != nil {
					h.logger.Error("failed to convert integration to API model", zap.Error(err))
					return echo.NewHTTPError(http.StatusInternalServerError, "failed to convert integration to API model")
				}
				apiIntegrations = append(apiIntegrations, *apiIntegration)
			}
			integrationGroupApi.Integrations = apiIntegrations
		}
		items = append(items, *integrationGroupApi)
	}

	return c.JSON(http.StatusOK, items)
}

// GetIntegrationGroup godoc
//
//	@Summary		Get integration group and the integrations
//	@Description	Get integration group and the integrations
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Param			populateIntegrations	query		bool	false	"Populate connections"	default(false)
//	@Param			integrationGroupName	path		string	true	"integrationGroupName"
//	@Success		200						{object}	models.IntegrationGroup
//	@Router			/integration/api/v1/integrations/integration-groups/{integrationGroupName} [get]
func (h *API) GetIntegrationGroup(c echo.Context) error {
	integrationGroupName := c.Param("integrationGroupName")

	populateIntegrations := false
	var err error
	if populateIntegrationsStr := c.QueryParam("populateIntegrations"); populateIntegrationsStr != "" {
		populateIntegrations, err = strconv.ParseBool(populateIntegrationsStr)
		if err != nil {
			return c.JSON(http.StatusBadRequest, "populateConnections is not a valid boolean")
		}
	}

	integrationGroup, err := h.database.GetIntegrationGroup(integrationGroupName)
	if err != nil {
		h.logger.Error("failed to list credentials", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to list credential")
	}

	steampipeConn, err := h.getSteampipeConn()
	if err != nil {
		h.logger.Error("failed to get steampipe connection", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get steampipe connection")
	}

	integrationGroupApi, err := entities.NewIntegrationGroup(c.Request().Context(), steampipeConn, *integrationGroup)
	if err != nil {
		h.logger.Error("failed to convert integration group to API model", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to convert integration group to API model")
	}
	if populateIntegrations {
		integrations, err := h.database.ListIntegrationsByFilters(integrationGroupApi.IntegrationIds, nil, nil, nil)
		if err != nil {
			h.logger.Error("failed to list integrations", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to list integrations")
		}
		var apiIntegrations []models.Integration
		for _, integration := range integrations {
			apiIntegration, err := integration.ToApi()
			if err != nil {
				h.logger.Error("failed to convert integration to API model", zap.Error(err))
				return echo.NewHTTPError(http.StatusInternalServerError, "failed to convert integration to API model")
			}
			apiIntegrations = append(apiIntegrations, *apiIntegration)
		}
		integrationGroupApi.Integrations = apiIntegrations
	}

	return c.JSON(http.StatusOK, integrationGroupApi)
}

// Get godoc
//
//	@Summary		Get credential
//	@Description	Get credential
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Success		200
//	@Param			IntegrationID	path	string	true	"IntegrationID"
//	@Router			/integration/api/v1/integrations/{IntegrationID} [get]
func (h *API) Get(c echo.Context) error {
	IntegrationID, err := uuid.Parse(c.Param("IntegrationID"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid request")
	}

	integration, err := h.database.GetIntegration(IntegrationID)
	if err != nil {
		h.logger.Error("failed to get integration", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get integration")
	}

	item, err := integration.ToApi()
	if err != nil {
		h.logger.Error("failed to convert integration to API model", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to convert integration to API model")
	}
	return c.JSON(http.StatusOK, item)
}

// Update godoc
//
//	@Summary		Get credential
//	@Description	Get credential
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Success		200
//	@Param			integrationId	path	string					true	"IntegrationID"
//	@Param			request			body	models.UpdateRequest	true	"Request"
//	@Router			/integration/api/v1/integrations/{integrationId} [post]
func (h *API) Update(c echo.Context) error {
	IntegrationID, err := uuid.Parse(c.Param("IntegrationID"))
	if err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid request")
	}

	var req models.UpdateRequest

	if err := c.Bind(&req); err != nil {
		return echo.NewHTTPError(http.StatusBadRequest, "invalid request")
	}

	integration, err := h.database.GetIntegration(IntegrationID)
	if err != nil {
		h.logger.Error("failed to get credential", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get credential")
	}

	credential, err := h.database.GetCredential(integration.CredentialID.String())
	if err != nil {
		h.logger.Error("failed to get credential", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get credential")
	}

	credentials, err := h.vault.Decrypt(c.Request().Context(), credential.Secret)
	if err != nil {
		h.logger.Error("failed to decrypt secret", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to decrypt config")
	}

	for k, v := range req.Credentials {
		credentials[k] = v
	}

	secret, err := h.vault.Encrypt(c.Request().Context(), credentials)
	if err != nil {
		h.logger.Error("failed to encrypt secret", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to encrypt config")
	}
	masked := make(map[string]any)
	for key, value := range req.Credentials {
		strValue, ok := value.(string) // Ensure the value is a string
		if !ok {
			// If it's not a string, just skip masking
			masked[key] = "not available"
			continue
		}

		// Get the last 5 characters, or the full string if it's shorter
		if len(strValue) > 5 {
			masked[key] = "*****" + strValue[len(strValue)-5:]
		} else {
			masked[key] = "*****" + strValue
		}
	}

	err = h.database.UpdateCredential(integration.CredentialID.String(), secret, masked, req.Description)
	if err != nil {
		h.logger.Error("failed to update credential", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to update credential")
	}

	return c.NoContent(http.StatusOK)
}

// ListIntegrationTypes godoc
//
//	@Summary		List integration types
//	@Description	List integration types
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Param			per_page		query		int		false	"PerPage"
//	@Param			cursor			query		int		false	"Cursor"
//	@Param			enabled			query		bool	false	"Enabled"
//	@Param			has_integration	query		bool	false	"Has Integrations"
//	@Param			sort_by			query		string	false	"Sort By (id, count)"
//	@Param			sort_order		query		string	false	"Sort Order (asc, desc)"
//
//	@Success		200				{object}	models.ListIntegrationTypesResponse
//	@Router			/integration/api/v1/integrations/types [get]
func (h *API) ListIntegrationTypes(c echo.Context) error {
	perPageStr := c.QueryParam("per_page")
	cursorStr := c.QueryParam("cursor")
	filteredEnabled := c.QueryParam("enabled")
	hasIntegration := c.QueryParam("has_integration")
	sortBy := c.QueryParam("sort_by")
	sortOrder := c.QueryParam("sort_order")
	var perPage, cursor int64
	if perPageStr != "" {
		perPage, _ = strconv.ParseInt(perPageStr, 10, 64)
	}
	if cursorStr != "" {
		cursor, _ = strconv.ParseInt(cursorStr, 10, 64)
	}

	plugins, err := h.database.ListPlugins()
	if err != nil {
		h.logger.Error("failed to list integration types", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to list integration types")
	}

	var items []models.ListIntegrationTypesItem
	for _, plugin := range plugins {
		integrations, err := h.database.ListIntegrationsByFilters(nil, []string{plugin.IntegrationType.String()}, nil, nil)
		if err != nil {
			h.logger.Error("failed to list integrations", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to list integrations")
		}
		if hasIntegration == "true" {
			if len(integrations) == 0 {
				continue
			}
		}
		count := models.IntegrationTypeIntegrationCount{}
		for _, i := range integrations {
			count.Total += 1
			if i.State == integration.IntegrationStateActive {
				count.Active += 1
			}
			if i.State == integration.IntegrationStateInactive {
				count.Inactive += 1
			}
			if i.State == integration.IntegrationStateArchived {
				count.Archived += 1
			}
			if i.State == integration.IntegrationStateSample {
				count.Demo += 1
			}
		}
		if plugin.OperationalStatus == models2.IntegrationPluginOperationalStatusDisabled {
			if filteredEnabled == "true" {
				continue
			}
		}
		items = append(items, models.ListIntegrationTypesItem{
			ID:           int64(plugin.ID),
			Name:         plugin.Name,
			Title:        plugin.Name,
			PlatformName: plugin.IntegrationType.String(),
			Tier:         plugin.Tier,
			Logo:         plugin.Icon,
			Enabled:      plugin.OperationalStatus == models2.IntegrationPluginOperationalStatusEnabled,
			Count:        count,
		})
	}

	totalCount := len(items)
	if sortOrder == "desc" {
		sort.Slice(items, func(i, j int) bool {
			return items[i].ID > items[j].ID
		})
		if sortBy == "count" {
			sort.Slice(items, func(i, j int) bool {
				if items[i].Count.Total == items[j].Count.Total {
					return items[i].ID < items[j].ID
				}
				return items[i].Count.Total > items[j].Count.Total
			})
		}
	} else {
		sort.Slice(items, func(i, j int) bool {
			return items[i].ID < items[j].ID
		})
		if sortBy == "count" {
			sort.Slice(items, func(i, j int) bool {
				if items[i].Count.Total == items[j].Count.Total {
					return items[i].ID < items[j].ID
				}
				return items[i].Count.Total < items[j].Count.Total
			})
		}
	}

	if perPage != 0 {
		if cursor == 0 {
			items = utils.Paginate(1, perPage, items)
		} else {
			items = utils.Paginate(cursor, perPage, items)
		}
	}

	return c.JSON(http.StatusOK, models.ListIntegrationTypesResponse{
		IntegrationTypes: items,
		TotalCount:       totalCount,
	})
}

// GetIntegrationType godoc
//
//	@Summary		Get integration type
//	@Description	Get integration type
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Success		200
//	@Param			integrationTypeId	path	string	true	"integrationTypeId"
//	@Router			/integration/api/v1/integrations/types/{integrationTypeId} [get]
func (h *API) GetIntegrationType(c echo.Context) error {
	integrationTypeId := c.Param("integrationTypeId")

	plugin, err := h.database.GetPluginByIntegrationType(integrationTypeId)
	if err != nil {
		h.logger.Error("failed to get credential", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get credential")
	}

	item := models.IntegrationType{
		Name: plugin.Name,
	}

	return c.JSON(http.StatusOK, item)
}

// GetIntegrationTypeUiSpec godoc
//
//	@Summary		Get integration type UI Spec
//	@Description	Get integration type UI Spec
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Success		200
//	@Param			integrationTypeId	path	string	true	"integrationTypeId"
//	@Router			/integration/api/v1/integrations/types/{integrationTypeId}/ui/spec [get]
func (h *API) GetIntegrationTypeUiSpec(c echo.Context) error {
	integrationTypeId := c.Param("integrationTypeId")

	entries, err := os.ReadDir("/")
	if err != nil {
		h.logger.Error("failed to read dir", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to read dir")
	}

	// Loop through entries
	for _, entry := range entries {
		if entry.IsDir() {
			h.logger.Info("Directory:", zap.String("path", entry.Name()))
		} else {
			h.logger.Info("File:", zap.String("path", entry.Name()))
		}
	}

	integrationType, ok := h.typesManager.GetIntegrationTypeMap()[integration.Type(integrationTypeId)]
	if !ok {
		return echo.NewHTTPError(http.StatusNotFound, "invalid integration type")
	}
	cnf, err := integrationType.GetConfiguration()
	if err != nil {
		h.logger.Error("failed to get configuration", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get configuration")
	}

	var result interface{}
	if err := json.Unmarshal(cnf.UISpec, &result); err != nil {
		h.logger.Error("failed to unmarshal the file", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to unmarshal the file")
	}

	return c.JSON(http.StatusOK, result)
}

// EnableIntegrationType godoc
//
//	@Summary		Enable integration type
//	@Description	Enable integration type
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Success		200
//	@Param			integration_type	path	string	true	"integration_type"
//	@Router			/integration/api/v1/integrations/types/{integration_type}/enable [put]
func (h *API) EnableIntegrationType(c echo.Context) error {
	integrationTypeName := c.Param("integration_type")

	err := h.EnableIntegrationTypeHelper(c.Request().Context(), integrationTypeName)
	if err != nil {
		return err
	}

	return c.NoContent(http.StatusOK)
}

// DisableIntegrationType godoc
//
//	@Summary		Enable integration type
//	@Description	Enable integration type
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Success		200
//	@Param			integration_type	path	string	true	"integration_type"
//	@Router			/integration/api/v1/integrations/types/{integration_type}/disable [put]
func (h *API) DisableIntegrationType(c echo.Context) error {
	ctx := c.Request().Context()

	integrationTypeName := c.Param("integration_type")

	plugin, _ := h.database.GetPluginByIntegrationType(integrationTypeName)
	if plugin == nil || (plugin.OperationalStatus == models2.IntegrationPluginOperationalStatusDisabled) {
		return echo.NewHTTPError(http.StatusBadRequest, "the integration type is already disabled")
	}

	var integrationTypes []integration.Type
	integrationTypes = append(integrationTypes, integration.Type(integrationTypeName))

	integrations, err := h.database.ListIntegration(integrationTypes)
	if err != nil {
		h.logger.Error("failed to list credentials", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to list credential")
	}
	if len(integrations) > 0 {
		return echo.NewHTTPError(http.StatusBadRequest, "integration type contains integrations, you can not disable it")
	}

	currentNamespace, ok := os.LookupEnv("CURRENT_NAMESPACE")
	if !ok {
		return echo.NewHTTPError(http.StatusInternalServerError, "current namespace lookup failed")
	}
	integrationType, ok := h.typesManager.GetIntegrationTypeMap()[integration.Type(integrationTypeName)]
	if !ok {
		return echo.NewHTTPError(http.StatusNotFound, "invalid integration type")
	}
	cnf, err := integrationType.GetConfiguration()
	if err != nil {
		h.logger.Error("failed to get configuration", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get configuration"+err.Error())
	}

	// Scheduled deployment
	var describerDeployment appsv1.Deployment
	err = h.kubeClient.Get(ctx, client.ObjectKey{
		Namespace: currentNamespace,
		Name:      cnf.DescriberDeploymentName,
	}, &describerDeployment)
	if err != nil {
		h.logger.Error("failed to get manual deployment", zap.Error(err))
	} else {
		err = h.kubeClient.Delete(ctx, &describerDeployment)
		if err != nil {
			h.logger.Error("failed to delete deployment", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to delete deployment")
		}
	}

	// Manual deployment
	var describerDeploymentManuals appsv1.Deployment
	err = h.kubeClient.Get(ctx, client.ObjectKey{
		Namespace: currentNamespace,
		Name:      cnf.DescriberDeploymentName + "-manuals",
	}, &describerDeploymentManuals)
	if err != nil {
		h.logger.Error("failed to get manual deployment", zap.Error(err))
	} else {
		err = h.kubeClient.Delete(ctx, &describerDeploymentManuals)
		if err != nil {
			h.logger.Error("failed to delete manual deployment", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to delete manual deployment")
		}
	}

	kedaEnabled, ok := os.LookupEnv("KEDA_ENABLED")
	if !ok {
		kedaEnabled = "false"
	}
	if strings.ToLower(kedaEnabled) == "true" {
		// Scheduled ScaledObject
		var describerScaledObject kedav1alpha1.ScaledObject
		err = h.kubeClient.Get(ctx, client.ObjectKey{
			Namespace: currentNamespace,
			Name:      cnf.DescriberDeploymentName + "-scaled-object",
		}, &describerScaledObject)
		if err != nil {
			h.logger.Error("failed to get scaled object", zap.Error(err))
		} else {
			err = h.kubeClient.Delete(ctx, &describerScaledObject)
			if err != nil {
				h.logger.Error("failed to delete scaled object", zap.Error(err))
				return echo.NewHTTPError(http.StatusInternalServerError, "failed to delete scaled object")
			}
		}

		// Manual ScaledObject
		var describerScaledObjectManuals kedav1alpha1.ScaledObject
		err = h.kubeClient.Get(ctx, client.ObjectKey{
			Namespace: currentNamespace,
			Name:      cnf.DescriberDeploymentName + "-manuals-scaled-object",
		}, &describerScaledObjectManuals)
		if err != nil {
			h.logger.Error("failed to get manual scaled object", zap.Error(err))
		} else {
			err = h.kubeClient.Delete(ctx, &describerScaledObjectManuals)
			if err != nil {
				h.logger.Error("failed to delete manual scaled object", zap.Error(err))
				return echo.NewHTTPError(http.StatusInternalServerError, "failed to delete manual scaled object")
			}
		}
	}

	plugin.OperationalStatus = models2.IntegrationPluginOperationalStatusDisabled

	err = h.database.UpdatePlugin(plugin)
	if err != nil {
		h.logger.Error("failed to update plugin", zap.Error(err), zap.String("id", plugin.PluginID))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to update plugin")
	}

	return c.NoContent(http.StatusOK)
}

// PurgeSampleData godoc
//
//	@Summary		Delete integrations with SAMPLE_INTEGRATION state
//	@Description	Delete integrations with SAMPLE_INTEGRATION state
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Success		200
//	@Router			/integration/api/v1/integrations/sample/purge [put]
func (h *API) PurgeSampleData(c echo.Context) error {
	integrations, err := h.database.ListSampleIntegrations()
	if err != nil {
		h.logger.Error("failed to list sample integrations", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to list sample integrations")
	}

	var integrationIDs []string
	for _, i := range integrations {
		integrationIDs = append(integrationIDs, i.IntegrationID.String())
	}

	err = h.database.DeleteSampleIntegrations()
	if err != nil {
		h.logger.Error("failed to delete sample integrations", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to delete sample integrations")
	}
	resp := struct {
		Integrations []string `json:"integrations"`
	}{
		Integrations: integrationIDs,
	}

	return c.JSON(http.StatusOK, resp)
}

// UpgradeIntegrationType godoc
//
//	@Summary		Upgrade integration type
//	@Description	Upgrade integration type
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Success		200
//	@Param			integration_type	path	string	true	"integration_type"
//	@Router			/integration/api/v1/integrations/types/{integration_type}/upgrade [put]
func (h *API) UpgradeIntegrationType(c echo.Context) error {
	ctx := c.Request().Context()

	integrationTypeName := c.Param("integration_type")

	plugin, _ := h.database.GetPluginByIntegrationType(integrationTypeName)
	if plugin == nil || (plugin.OperationalStatus == models2.IntegrationPluginOperationalStatusDisabled) {
		return echo.NewHTTPError(http.StatusBadRequest, "the integration type is not enabled")
	}

	var integrationTypes []integration.Type
	integrationTypes = append(integrationTypes, integration.Type(integrationTypeName))

	currentNamespace, ok := os.LookupEnv("CURRENT_NAMESPACE")
	if !ok {
		return echo.NewHTTPError(http.StatusInternalServerError, "current namespace lookup failed")
	}
	integrationType, ok := h.typesManager.GetIntegrationTypeMap()[integration.Type(integrationTypeName)]
	if !ok {
		return echo.NewHTTPError(http.StatusNotFound, "invalid integration type")
	}
	cnf, err := integrationType.GetConfiguration()
	if err != nil {
		h.logger.Error("failed to get configuration", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get configuration")
	}

	// Scheduled deployment
	var describerDeployment appsv1.Deployment
	err = h.kubeClient.Get(ctx, client.ObjectKey{
		Namespace: currentNamespace,
		Name:      cnf.DescriberDeploymentName,
	}, &describerDeployment)
	if err != nil {
		h.logger.Error("failed to get deployment", zap.Error(err))
	} else {
		err = h.kubeClient.Delete(ctx, &describerDeployment)
		if err != nil {
			h.logger.Error("failed to delete deployment", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to delete deployment")
		}
	}

	describerDeployment.ObjectMeta.Name = cnf.DescriberDeploymentName
	describerDeployment.Spec.Selector.MatchLabels["app"] = cnf.DescriberDeploymentName
	describerDeployment.Spec.Template.ObjectMeta.Labels["app"] = cnf.DescriberDeploymentName
	describerDeployment.Spec.Template.Spec.ServiceAccountName = "og-describer"

	container := describerDeployment.Spec.Template.Spec.Containers[0]
	container.Name = cnf.DescriberDeploymentName
	container.Image = fmt.Sprintf("%s:%s", plugin.DescriberURL, plugin.DescriberTag)
	container.Command = []string{cnf.DescriberRunCommand}
	describerDeployment.Spec.Template.Spec.Containers[0] = container

	newDeployment := appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      cnf.DescriberDeploymentName,
			Namespace: currentNamespace,
			Labels: map[string]string{
				"app": cnf.DescriberDeploymentName,
			},
		},
		Spec: describerDeployment.Spec,
	}

	err = h.kubeClient.Create(ctx, &newDeployment)
	if err != nil {
		return err
	}

	// Manual deployment
	var describerDeploymentManuals appsv1.Deployment
	err = h.kubeClient.Get(ctx, client.ObjectKey{
		Namespace: currentNamespace,
		Name:      cnf.DescriberDeploymentName + "-manuals",
	}, &describerDeploymentManuals)
	if err != nil {
		h.logger.Error("failed to get manual deployment", zap.Error(err))
	} else {
		err = h.kubeClient.Delete(ctx, &describerDeploymentManuals)
		if err != nil {
			h.logger.Error("failed to delete manual deployment", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to delete manual deployment")
		}
	}

	describerDeploymentManuals.ObjectMeta.Name = cnf.DescriberDeploymentName + "-manuals"
	describerDeploymentManuals.Spec.Selector.MatchLabels["app"] = cnf.DescriberDeploymentName + "-manuals"
	describerDeploymentManuals.Spec.Template.ObjectMeta.Labels["app"] = cnf.DescriberDeploymentName + "-manuals"
	describerDeploymentManuals.Spec.Template.Spec.ServiceAccountName = "og-describer"

	containerManuals := describerDeploymentManuals.Spec.Template.Spec.Containers[0]
	containerManuals.Name = cnf.DescriberDeploymentName
	containerManuals.Image = fmt.Sprintf("%s:%s", plugin.DescriberURL, plugin.DescriberTag)
	containerManuals.Command = []string{cnf.DescriberRunCommand}
	describerDeploymentManuals.Spec.Template.Spec.Containers[0] = containerManuals

	newDeploymentManuals := appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      cnf.DescriberDeploymentName + "-manuals",
			Namespace: currentNamespace,
			Labels: map[string]string{
				"app": cnf.DescriberDeploymentName + "-manuals",
			},
		},
		Spec: describerDeploymentManuals.Spec,
	}

	err = h.kubeClient.Create(ctx, &newDeploymentManuals)
	if err != nil {
		return err
	}

	return c.NoContent(http.StatusOK)
}

func (h *API) EnableIntegrationTypeHelper(ctx context.Context, integrationTypeName string) error {
	currentNamespace, ok := os.LookupEnv("CURRENT_NAMESPACE")
	if !ok {
		return echo.NewHTTPError(http.StatusInternalServerError, "current namespace lookup failed")
	}

	plugin, err := h.database.GetPluginByIntegrationType(integrationTypeName)
	if err != nil {
		h.logger.Error("failed to get integration type", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get integration type")
	}
	kedaEnabled, ok := os.LookupEnv("KEDA_ENABLED")
	if !ok {
		kedaEnabled = "false"
	}

	// Scheduled deployment
	var describerDeployment appsv1.Deployment
	templateDeploymentFile, err := os.Open(TemplateDeploymentPath)
	if err != nil {
		h.logger.Error("failed to open template deployment file", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to open template deployment file")
	}
	defer templateDeploymentFile.Close()

	data, err := ioutil.ReadAll(templateDeploymentFile)
	if err != nil {
		h.logger.Error("failed to read template deployment file", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to read template deployment file")
	}

	err = yaml.Unmarshal(data, &describerDeployment)
	if err != nil {
		h.logger.Error("failed to unmarshal template deployment file", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to unmarshal template deployment file")
	}

	integrationType, ok := h.typesManager.GetIntegrationTypeMap()[integration.Type(integrationTypeName)]
	if !ok {
		return echo.NewHTTPError(http.StatusNotFound, "invalid integration type")
	}
	cnf, err := integrationType.GetConfiguration()
	if err != nil {
		h.logger.Error("failed to get integration type configuration", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to get integration type configuration")
	}

	describerDeployment.ObjectMeta.Name = cnf.DescriberDeploymentName
	describerDeployment.ObjectMeta.Namespace = currentNamespace
	if kedaEnabled == "true" {
		describerDeployment.Spec.Replicas = aws.Int32(0)
	} else {
		describerDeployment.Spec.Replicas = aws.Int32(5)
	}
	describerDeployment.Spec.Selector.MatchLabels["app"] = cnf.DescriberDeploymentName
	describerDeployment.Spec.Template.ObjectMeta.Labels["app"] = cnf.DescriberDeploymentName
	describerDeployment.Spec.Template.Spec.ServiceAccountName = "og-describer"

	container := describerDeployment.Spec.Template.Spec.Containers[0]
	container.Name = cnf.DescriberDeploymentName
	container.Image = fmt.Sprintf("%s:%s", plugin.DescriberURL, plugin.DescriberTag)
	container.Command = []string{cnf.DescriberRunCommand}
	natsUrl, ok := os.LookupEnv("NATS_URL")
	if ok {
		container.Env = append(container.Env, v1.EnvVar{
			Name:  "NATS_URL",
			Value: natsUrl,
		})
	}
	describerDeployment.Spec.Template.Spec.Containers[0] = container

	newDeployment := appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      cnf.DescriberDeploymentName,
			Namespace: currentNamespace,
			Labels: map[string]string{
				"app": cnf.DescriberDeploymentName,
			},
		},
		Spec: describerDeployment.Spec,
	}

	err = h.kubeClient.Create(ctx, &newDeployment)
	if err != nil {
		return err
	}

	// Manual deployment
	var describerDeploymentManuals appsv1.Deployment
	templateManualsDeploymentFile, err := os.Open(TemplateManualsDeploymentPath)
	if err != nil {
		h.logger.Error("failed to open template manuals deployment file", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to open template manuals deployment file")
	}
	defer templateManualsDeploymentFile.Close()

	data, err = ioutil.ReadAll(templateManualsDeploymentFile)
	if err != nil {
		h.logger.Error("failed to read template manuals deployment file", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to read template manuals deployment file")
	}

	err = yaml.Unmarshal(data, &describerDeploymentManuals)
	if err != nil {
		h.logger.Error("failed to unmarshal template manuals deployment file", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to unmarshal template manuals deployment file")
	}

	describerDeploymentManuals.ObjectMeta.Name = cnf.DescriberDeploymentName + "-manuals"
	describerDeploymentManuals.ObjectMeta.Namespace = currentNamespace
	if kedaEnabled == "true" {
		describerDeploymentManuals.Spec.Replicas = aws.Int32(0)
	} else {
		describerDeploymentManuals.Spec.Replicas = aws.Int32(2)
	}
	describerDeploymentManuals.Spec.Selector.MatchLabels["app"] = cnf.DescriberDeploymentName + "-manuals"
	describerDeploymentManuals.Spec.Template.ObjectMeta.Labels["app"] = cnf.DescriberDeploymentName + "-manuals"
	describerDeploymentManuals.Spec.Template.Spec.ServiceAccountName = "og-describer"

	containerManuals := describerDeploymentManuals.Spec.Template.Spec.Containers[0]
	containerManuals.Name = cnf.DescriberDeploymentName
	containerManuals.Image = fmt.Sprintf("%s:%s", plugin.DescriberURL, plugin.DescriberTag)
	containerManuals.Command = []string{cnf.DescriberRunCommand}
	natsUrl, ok = os.LookupEnv("NATS_URL")
	if ok {
		containerManuals.Env = append(containerManuals.Env, v1.EnvVar{
			Name:  "NATS_URL",
			Value: natsUrl,
		})
	}
	describerDeploymentManuals.Spec.Template.Spec.Containers[0] = containerManuals

	newDeploymentManuals := appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      cnf.DescriberDeploymentName + "-manuals",
			Namespace: currentNamespace,
			Labels: map[string]string{
				"app": cnf.DescriberDeploymentName + "-manuals",
			},
		},
		Spec: describerDeploymentManuals.Spec,
	}

	err = h.kubeClient.Create(ctx, &newDeploymentManuals)
	if err != nil {
		return err
	}

	if strings.ToLower(kedaEnabled) == "true" {
		// Scheduled ScaledObject
		var describerScaledObject kedav1alpha1.ScaledObject
		templateScaledObjectFile, err := os.Open(TemplateScaledObjectPath)
		if err != nil {
			h.logger.Error("failed to open template scaledobject file", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to open template scaledobject file")
		}
		defer templateScaledObjectFile.Close()

		data, err = ioutil.ReadAll(templateScaledObjectFile)
		if err != nil {
			h.logger.Error("failed to read template manuals deployment file", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to read template scaledobject file")
		}

		err = yaml.Unmarshal(data, &describerScaledObject)
		if err != nil {
			h.logger.Error("failed to unmarshal template deployment file", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to unmarshal template deployment file")
		}

		describerScaledObject.Spec.ScaleTargetRef.Name = cnf.DescriberDeploymentName

		trigger := describerScaledObject.Spec.Triggers[0]
		trigger.Metadata["stream"] = cnf.NatsStreamName
		soNatsUrl, _ := os.LookupEnv("SCALED_OBJECT_NATS_URL")
		trigger.Metadata["natsServerMonitoringEndpoint"] = soNatsUrl
		trigger.Metadata["consumer"] = cnf.NatsConsumerGroup + "-service"
		describerScaledObject.Spec.Triggers[0] = trigger

		newScaledObject := kedav1alpha1.ScaledObject{
			ObjectMeta: metav1.ObjectMeta{
				Name:      cnf.DescriberDeploymentName + "-scaled-object",
				Namespace: currentNamespace,
			},
			Spec: describerScaledObject.Spec,
		}

		err = h.kubeClient.Create(ctx, &newScaledObject)
		if err != nil {
			return err
		}

		// Manual ScaledObject
		var describerScaledObjectManuals kedav1alpha1.ScaledObject
		templateManualsScaledObjectFile, err := os.Open(TemplateManualsScaledObjectPath)
		if err != nil {
			h.logger.Error("failed to open template manuals scaledobject file", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to open template manuals scaledobject file")
		}
		defer templateManualsScaledObjectFile.Close()

		data, err = ioutil.ReadAll(templateManualsScaledObjectFile)
		if err != nil {
			h.logger.Error("failed to read template manuals deployment file", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to read template manuals scaledobject file")
		}

		err = yaml.Unmarshal(data, &describerScaledObjectManuals)
		if err != nil {
			h.logger.Error("failed to unmarshal template deployment file", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to unmarshal template deployment file")
		}

		describerScaledObjectManuals.Spec.ScaleTargetRef.Name = cnf.DescriberDeploymentName + "-manuals"

		triggerManuals := describerScaledObjectManuals.Spec.Triggers[0]
		triggerManuals.Metadata["stream"] = cnf.NatsStreamName
		triggerManuals.Metadata["natsServerMonitoringEndpoint"] = soNatsUrl
		triggerManuals.Metadata["consumer"] = cnf.NatsConsumerGroupManuals + "-service"
		describerScaledObjectManuals.Spec.Triggers[0] = triggerManuals

		newScaledObjectManuals := kedav1alpha1.ScaledObject{
			ObjectMeta: metav1.ObjectMeta{
				Name:      cnf.DescriberDeploymentName + "-manuals-scaled-object",
				Namespace: currentNamespace,
			},
			Spec: describerScaledObjectManuals.Spec,
		}

		err = h.kubeClient.Create(ctx, &newScaledObjectManuals)
		if err != nil {
			return err
		}
	}

	err = h.database.UpdatePlugin(&models2.IntegrationPlugin{
		PluginID:          plugin.PluginID,
		IntegrationType:   plugin.IntegrationType,
		InstallState:      models2.IntegrationTypeInstallStateInstalled,
		OperationalStatus: models2.IntegrationPluginOperationalStatusEnabled,
		URL:               plugin.URL,
	})
	if err != nil {
		h.logger.Error("failed to update plugin", zap.Error(err), zap.String("id", plugin.IntegrationType.String()))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to update plugin")
	}

	return nil
}

// ListIntegrationTypeResourceTypes godoc
//
//	@Summary		List integration type resource types
//	@Description	List integration type resource types
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Param			per_page			query		int		false	"PerPage"
//	@Param			cursor				query		int		false	"Cursor"
//	@Param			integration_type	path		string	true	"integration_type"
//	@Success		200					{object}	models.ListIntegrationTypesResponse
//	@Router			/integration/api/v1/integrations/types/:integration_type/resource_types [get]
func (h *API) ListIntegrationTypeResourceTypes(c echo.Context) error {
	integrationType := c.Param("integration_type")

	perPageStr := c.QueryParam("per_page")
	cursorStr := c.QueryParam("cursor")
	var perPage, cursor int64
	if perPageStr != "" {
		perPage, _ = strconv.ParseInt(perPageStr, 10, 64)
	}
	if cursorStr != "" {
		cursor, _ = strconv.ParseInt(cursorStr, 10, 64)
	}

	var items []models.ResourceTypeConfiguration
	if it, ok := h.typesManager.GetIntegrationTypeMap()[h.typesManager.ParseType(integrationType)]; ok {
		resourceTypes, err := it.GetResourceTypesByLabels(nil)
		if err != nil {
			h.logger.Error("failed to list integration type resource types", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to list integration type resource types")
		}
		for _, rtConfig := range resourceTypes {
			if !rtConfig.IsEmpty() {
				items = append(items, models.ApiResourceTypeConfiguration(rtConfig))
			} else {
				items = append(items, models.ResourceTypeConfiguration{
					Name:            rtConfig.Name,
					IntegrationType: h.typesManager.ParseType(integrationType),
				})
			}
		}
	} else {
		return echo.NewHTTPError(http.StatusInternalServerError, "integration type resource types not found")
	}

	totalCount := len(items)
	sort.Slice(items, func(i, j int) bool {
		return items[i].Name > items[j].Name
	})

	if perPage != 0 {
		if cursor == 0 {
			items = utils.Paginate(1, perPage, items)
		} else {
			items = utils.Paginate(cursor, perPage, items)
		}
	}

	return c.JSON(http.StatusOK, models.ListIntegrationTypeResourceTypesResponse{
		ResourceTypes: items,
		TotalCount:    totalCount,
	})
}

// GetIntegrationTypeResourceType godoc
//
//	@Summary		List integration type resource types
//	@Description	List integration type resource types
//	@Security		BearerToken
//	@Tags			credentials
//	@Produce		json
//	@Param			integration_type	path		string	true	"integration_type"
//	@Param			resource_type		path		string	true	"resource_type"
//	@Success		200					{object}	models.ListIntegrationTypesResponse
//	@Router			/integration/api/v1/integrations/types/:integration_type/resource_types/:resource_type [get]
func (h *API) GetIntegrationTypeResourceType(c echo.Context) error {
	integrationType := c.Param("integration_type")
	resourceType := c.Param("resource_type")

	if it, ok := h.typesManager.GetIntegrationTypeMap()[h.typesManager.ParseType(integrationType)]; ok {
		resourceTypes, err := it.GetResourceTypesByLabels(nil)
		if err != nil {
			h.logger.Error("failed to list integration type resource types", zap.Error(err))
			return echo.NewHTTPError(http.StatusInternalServerError, "failed to list integration type resource types")
		}
		for _, rtConfig := range resourceTypes {
			if rtConfig.Name == resourceType {
				return c.JSON(http.StatusOK, models.ApiResourceTypeConfiguration(rtConfig))
			}
		}
		return echo.NewHTTPError(http.StatusInternalServerError, "resource type not found")

	} else {
		return echo.NewHTTPError(http.StatusInternalServerError, "integration type resource types not found")
	}
}

// SetResourceTypesForIntegration godoc
//
// @Summary			Set valid resource types for an integration
// @Description		Set valid resource types for an integration
// @Security		BearerToken
// @Tags			integration_types
// @Produce			json
// @Param			integration_id	path	string	true	"Integration id"
// @Param			request	body	models.SetResourceTypesForIntegration	true	"Request"
// @Success			200	{object}
// @Router			/integration/api/v1/integrations/:integration_id/resource [put]
func (a *API) SetResourceTypesForIntegration(c echo.Context) error {
	integrationID, err := uuid.Parse(c.Param("integration_id"))
	if err != nil {
		a.logger.Error("failed to parse integration id", zap.Error(err))
		return echo.NewHTTPError(http.StatusInternalServerError, "failed to parse integration id")
	}

	req := new(models.SetResourceTypesForIntegration)
	if err = c.Bind(req); err != nil {
		return echo.NewHTTPError(400, "invalid request")
	}

	err = a.database.SetIntegrationResourcetypes(&models2.IntegrationResourcetypes{
		IntegrationID: integrationID,
		ResourceTypes: req.ResourceTypes,
	})

	return c.NoContent(http.StatusOK)
}
