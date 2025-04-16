package compliance

import (
	"encoding/json"
	"fmt"
	"github.com/opengovern/opensecurity/jobs/post-install-job/config"
	"github.com/opengovern/opensecurity/jobs/post-install-job/job/migrations/shared"
	"github.com/opengovern/opensecurity/jobs/post-install-job/utils"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"strings"

	"github.com/goccy/go-yaml"
	"github.com/jackc/pgtype"
	"github.com/opengovern/og-util/pkg/model"
	"github.com/opengovern/opensecurity/jobs/post-install-job/job/git"
	"github.com/opengovern/opensecurity/pkg/types"
	"github.com/opengovern/opensecurity/services/compliance/db"
	"github.com/opengovern/opensecurity/services/core/db/models"
	"go.uber.org/zap"
)

type GitParser struct {
	logger             *zap.Logger
	benchmarks         map[string]*db.Benchmark
	frameworksChildren map[string][]string
	frameworksControls map[string][]string
	controls           []db.Control
	policies           []db.Policy
	policyParamValues  []models.PolicyParameterValues
	controlsPolicies   map[string]db.Policy
	namedPolicies      map[string]NamedQuery
	Comparison         *git.ComparisonResultGrouped

	manualRemediationMap       map[string]string
	cliRemediationMap          map[string]string
	guardrailRemediationMap    map[string]string
	programmaticRemediationMap map[string]string
	noncomplianceCostMap       map[string]string
	usefulnessExampleMap       map[string]string
	explanationMap             map[string]string
}

func populateMdMapFromPath(path string) (map[string]string, error) {
	result := make(map[string]string)
	err := filepath.WalkDir(path, func(path string, d fs.DirEntry, err error) error {
		if !strings.HasSuffix(path, ".md") {
			return nil
		}
		id := strings.ToLower(strings.TrimSuffix(filepath.Base(path), ".md"))
		content, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		result[id] = string(content)
		return nil
	})
	if err != nil {
		return nil, err
	}
	return result, nil
}

func (g *GitParser) ExtractControls(complianceControlsPath string, controlEnrichmentBasePath string) error {
	var err error

	g.manualRemediationMap, err = populateMdMapFromPath(path.Join(controlEnrichmentBasePath, "tags", "remediation", "manual"))
	if err != nil {
		g.logger.Warn("failed to load manual remediation", zap.Error(err))
	}

	g.cliRemediationMap, err = populateMdMapFromPath(path.Join(controlEnrichmentBasePath, "tags", "remediation", "cli"))
	if err != nil {
		g.logger.Warn("failed to load cli remediation", zap.Error(err))
	}

	g.guardrailRemediationMap, err = populateMdMapFromPath(path.Join(controlEnrichmentBasePath, "tags", "remediation", "guardrail"))
	if err != nil {
		g.logger.Warn("failed to load cli remediation", zap.Error(err))
	}

	g.programmaticRemediationMap, err = populateMdMapFromPath(path.Join(controlEnrichmentBasePath, "tags", "remediation", "programmatic"))
	if err != nil {
		g.logger.Warn("failed to load cli remediation", zap.Error(err))
	}

	g.noncomplianceCostMap, err = populateMdMapFromPath(path.Join(controlEnrichmentBasePath, "tags", "noncompliance-cost"))
	if err != nil {
		g.logger.Warn("failed to load cli remediation", zap.Error(err))
	}

	g.usefulnessExampleMap, err = populateMdMapFromPath(path.Join(controlEnrichmentBasePath, "tags", "usefulness-example"))
	if err != nil {
		g.logger.Warn("failed to load cli remediation", zap.Error(err))
	}

	g.explanationMap, err = populateMdMapFromPath(path.Join(controlEnrichmentBasePath, "tags", "explanation"))
	if err != nil {
		g.logger.Warn("failed to load cli remediation", zap.Error(err))
	}

	return filepath.WalkDir(complianceControlsPath, func(path string, d fs.DirEntry, err error) error {
		if strings.HasSuffix(path, ".yaml") {
			content, err := os.ReadFile(path)
			if err != nil {
				g.logger.Error("failed to read yaml", zap.String("path", path), zap.Error(err))
				return err
			}

			var data map[string]interface{}
			if err := yaml.Unmarshal(content, &data); err != nil {
				g.logger.Error("failed to unmarshal yaml", zap.String("path", path), zap.Error(err))
				return fmt.Errorf("cannot parse YAML as map: %w", err)
			}

			if data["id"] != nil && data["policy"] != nil && data["severity"] != nil {
				if err = g.parseControlFile(content, path); err != nil {
					g.logger.Error("failed to parse control", zap.String("path", path), zap.Error(err))
					return err
				}
			} else if data["id"] != nil && data["definition"] != nil && data["language"] != nil {
				if err = g.parsePolicyFile(content, path); err != nil {
					g.logger.Error("failed to parse control", zap.String("path", path), zap.Error(err))
					return err
				}
			}
		}
		return nil
	})
}

func (g *GitParser) ExtractParameters() error {
	content, err := os.ReadFile(config.ParametersYamlPath)
	if err != nil {
		g.logger.Error("failed to read yaml", zap.String("path", config.ParametersYamlPath), zap.Error(err))
		return err
	}

	if err = g.parseParameterDefaulValuesFile(content, config.ParametersYamlPath); err != nil {
		g.logger.Error("failed to parse control", zap.String("path", config.ParametersYamlPath), zap.Error(err))
		return err
	}

	return nil
}

func (g *GitParser) parseParameterDefaulValuesFile(content []byte, path string) error {
	var parametersFile shared.ParameterDefaultValueFile
	err := yaml.Unmarshal(content, &parametersFile)
	if err != nil {
		g.logger.Error("failed to unmarshal policy", zap.String("path", path), zap.Error(err))
		return err
	}

	if parametersFile.Type != "parameters" {
		return fmt.Errorf("manifest type %s is not supported, should be parameters", parametersFile.Type)
	}

	for _, p := range parametersFile.Parameters {
		if len(p.Controls) == 0 {
			g.policyParamValues = append(g.policyParamValues, models.PolicyParameterValues{
				Key:   p.Key,
				Value: p.Value,
			})
		} else {
			for _, c := range p.Controls {
				g.policyParamValues = append(g.policyParamValues, models.PolicyParameterValues{
					Key:       p.Key,
					ControlID: c,
					Value:     p.Value,
				})
			}
		}
	}

	return nil
}

func (g *GitParser) ExtractPolicies(compliancePoliciesPath string) error {
	return filepath.WalkDir(compliancePoliciesPath, func(path string, d fs.DirEntry, err error) error {
		if strings.HasSuffix(path, ".yaml") {
			content, err := os.ReadFile(path)
			if err != nil {
				g.logger.Error("failed to read yaml", zap.String("path", path), zap.Error(err))
				return err
			}

			var data map[string]interface{}
			if err := yaml.Unmarshal(content, &data); err != nil {
				g.logger.Error("failed to unmarshal yaml", zap.String("path", path), zap.Error(err))
				return fmt.Errorf("cannot parse YAML as map: %w", err)
			}

			if data["type"] != nil {
				ty, ok := data["type"].(string)
				if ok {
					if ty == "control" {
						if data["policy"] != nil && data["severity"] != nil {
							if err = g.parseControlFile(content, path); err != nil {
								g.logger.Error("failed to parse control", zap.String("path", path), zap.Error(err))
								return err
							}
						} else {
							g.logger.Error("fields policy and severity should be defined for control", zap.String("path", path))
						}
					} else if ty == "policy" {
						if data["definition"] != nil && data["language"] != nil {
							if err = g.parsePolicyFile(content, path); err != nil {
								g.logger.Error("failed to parse control", zap.String("path", path), zap.Error(err))
								return err
							}
						} else {
							g.logger.Error("fields definition and language should be defined for policy", zap.String("path", path))
						}
					} else {
						g.logger.Error("unclassified type", zap.String("type", ty))
					}
				} else {
					g.logger.Error("no type defined", zap.String("path", path))
				}
			} else {
				g.logger.Error("no type defined", zap.String("path", path))
			}

		}
		return nil
	})
}

func (g *GitParser) parsePolicyFile(content []byte, path string) error {
	var policy shared.Policy
	err := yaml.Unmarshal(content, &policy)
	if err != nil {
		g.logger.Error("failed to unmarshal policy", zap.String("path", path), zap.Error(err))
		return err
	}

	if policy.ID == nil {
		g.logger.Error("policy id should not be nil", zap.String("path", path))
		return fmt.Errorf("policy id should not be nil")
	}

	listOfTables, err := utils.ExtractTableRefsFromPolicy(policy.Language, policy.Definition)
	if err != nil {
		g.logger.Error("extract control failed: failed to extract table refs from query", zap.String("policy-id", *policy.ID), zap.Error(err))
		return nil
	}

	parameters, err := utils.ExtractParameters(policy.Language, policy.Definition)
	if err != nil {
		g.logger.Error("extract control failed: failed to extract parameters from query", zap.String("policy-id", *policy.ID), zap.Error(err))
		return nil
	}

	q := db.Policy{
		ID:              *policy.ID,
		Title:           policy.Title,
		Description:     policy.Description,
		ExternalPolicy:  true,
		Definition:      policy.Definition,
		PrimaryResource: policy.PrimaryResource,
		ListOfResources: listOfTables,
		Language:        policy.Language,
		RegoPolicies:    policy.RegoPolicies,
	}

	for _, parameter := range parameters {
		q.Parameters = append(q.Parameters, db.PolicyParameter{
			PolicyID: *policy.ID,
			Key:      parameter,
		})
	}

	g.policies = append(g.policies, q)

	return nil
}

func (g *GitParser) parseControlFile(content []byte, path string) error {
	var control Control
	err := yaml.Unmarshal(content, &control)
	if err != nil {
		g.logger.Error("failed to unmarshal control", zap.String("path", path), zap.Error(err))
		return err
	}
	tags := make([]db.ControlTag, 0, len(control.Tags))
	for tagKey, tagValue := range control.Tags {
		tags = append(tags, db.ControlTag{
			Tag: model.Tag{
				Key:   tagKey,
				Value: tagValue,
			},
			ControlID: control.ID,
		})
	}
	if v, ok := g.manualRemediationMap[strings.ToLower(control.ID)]; ok {
		tags = append(tags, db.ControlTag{
			Tag: model.Tag{
				Key:   "x-opengovernance-manual-remediation",
				Value: []string{v},
			},
			ControlID: control.ID,
		})
	}
	if v, ok := g.cliRemediationMap[strings.ToLower(control.ID)]; ok {
		tags = append(tags, db.ControlTag{
			Tag: model.Tag{
				Key:   "x-opengovernance-cli-remediation",
				Value: []string{v},
			},
			ControlID: control.ID,
		})
	}
	if v, ok := g.guardrailRemediationMap[strings.ToLower(control.ID)]; ok {
		tags = append(tags, db.ControlTag{
			Tag: model.Tag{
				Key:   "x-opengovernance-guardrail-remediation",
				Value: []string{v},
			},
			ControlID: control.ID,
		})
	}
	if v, ok := g.programmaticRemediationMap[strings.ToLower(control.ID)]; ok {
		tags = append(tags, db.ControlTag{
			Tag: model.Tag{
				Key:   "x-opengovernance-programmatic-remediation",
				Value: []string{v},
			},
			ControlID: control.ID,
		})
	}
	if v, ok := g.noncomplianceCostMap[strings.ToLower(control.ID)]; ok {
		tags = append(tags, db.ControlTag{
			Tag: model.Tag{
				Key:   "x-opengovernance-noncompliance-cost",
				Value: []string{v},
			},
			ControlID: control.ID,
		})
	}
	if v, ok := g.explanationMap[strings.ToLower(control.ID)]; ok {
		tags = append(tags, db.ControlTag{
			Tag: model.Tag{
				Key:   "x-opengovernance-explanation",
				Value: []string{v},
			},
			ControlID: control.ID,
		})
	}
	if v, ok := g.usefulnessExampleMap[strings.ToLower(control.ID)]; ok {
		tags = append(tags, db.ControlTag{
			Tag: model.Tag{
				Key:   "x-opengovernance-usefulness-example",
				Value: []string{v},
			},
			ControlID: control.ID,
		})
	}
	if control.Severity == "" {
		control.Severity = "low"
	}

	c := db.Control{
		ID:              control.ID,
		Title:           control.Title,
		Description:     control.Description,
		Tags:            tags,
		IntegrationType: control.IntegrationType,
		Enabled:         true,
		Benchmarks:      nil,
		Severity:        types.ParseComplianceResultSeverity(control.Severity),
	}

	if control.Policy != nil {
		if control.Policy.Ref != nil {
			c.PolicyID = control.Policy.Ref
			c.ExternalPolicy = true
		} else {
			listOfTables, err := utils.ExtractTableRefsFromPolicy(control.Policy.Language, control.Policy.Definition)
			if err != nil {
				g.logger.Error("extract control failed: failed to extract table refs from query", zap.String("control-id", control.ID), zap.Error(err))
				return nil
			}

			parameters, err := utils.ExtractParameters(control.Policy.Language, control.Policy.Definition)
			if err != nil {
				g.logger.Error("extract control failed: failed to extract parameters from query", zap.String("control-id", control.ID), zap.Error(err))
				return nil
			}

			q := db.Policy{
				ID:              control.ID,
				Definition:      control.Policy.Definition,
				IntegrationType: control.IntegrationType,
				PrimaryResource: control.Policy.PrimaryResource,
				ListOfResources: listOfTables,
				Language:        control.Policy.Language,
				RegoPolicies:    control.Policy.RegoPolicies,
			}
			g.controlsPolicies[control.ID] = q

			controlParameterValues := make(map[string]string)
			for _, parameter := range control.Parameters {
				controlParameterValues[parameter.Key] = parameter.Value
			}

			for _, parameter := range parameters {
				q.Parameters = append(q.Parameters, db.PolicyParameter{
					PolicyID: control.ID,
					Key:      parameter,
				})
				if g.checkGlobalParameters(parameter) {
					continue
				}
				if v, ok := controlParameterValues[parameter]; ok {
					g.policyParamValues = append(g.policyParamValues, models.PolicyParameterValues{
						Key:       parameter,
						Value:     v,
						ControlID: control.ID,
					})
				} else {
					g.logger.Error("extract control failed: control does not contain parameter value", zap.String("control-id", control.ID),
						zap.String("parameter", parameter))
					return nil
				}
			}
			g.policies = append(g.policies, q)
			c.PolicyID = &control.ID
		}
	}
	g.controls = append(g.controls, c)
	return nil
}

func (g *GitParser) checkGlobalParameters(param string) bool {
	for _, p := range g.policyParamValues {
		if p.Key == param && p.ControlID == "" {
			return true
		}
	}
	return false
}

func (g *GitParser) ExtractFrameworks(complianceBenchmarksPath string) error {
	var frameworks []Framework
	err := filepath.WalkDir(complianceBenchmarksPath, func(path string, d fs.DirEntry, err error) error {
		if !strings.HasSuffix(filepath.Base(path), ".yaml") {
			return nil
		}

		content, err := os.ReadFile(path)
		if err != nil {
			g.logger.Error("failed to read benchmark", zap.String("path", path), zap.Error(err))
			return err
		}

		var temp map[string]interface{}
		err = yaml.Unmarshal(content, &temp)
		if err != nil {
			g.logger.Error("failed to unmarshal benchmark for validation", zap.String("path", path), zap.Error(err))
			return err
		}

		// Check for required fields
		id, hasID := temp["id"].(string)
		typeField, hasType := temp["type"].(string)

		if !hasID || id == "" {
			g.logger.Error("missing or empty 'id' field", zap.String("path", path))
			return fmt.Errorf("missing or empty 'id' field in file: %s", path)
		}

		if !hasType || typeField == "" {
			g.logger.Error("missing or empty 'type' field", zap.String("path", path))
			return fmt.Errorf("missing or empty 'type' field in file: %s", path)
		}

		if typeField == "framework" {
			var obj Framework
			err = yaml.Unmarshal(content, &obj)
			if err != nil {
				g.logger.Error("failed to unmarshal framework", zap.String("path", path), zap.Error(err))
				return err
			}

			frameworks = append(frameworks, obj)
		} else if typeField == "control-group" {
			var obj Framework
			err = yaml.Unmarshal(content, &obj)
			if err != nil {
				g.logger.Error("failed to unmarshal benchmark", zap.String("path", path), zap.Error(err))
				return err
			}

			frameworks = append(frameworks, obj)
		} else {
			g.logger.Error("this file should be deprecated", zap.String("path", path))
		}

		return nil
	})

	if err != nil {
		return err
	}

	err = g.HandleFrameworks(frameworks)
	if err != nil {
		return err
	}

	newBenchmarks := make(map[string]*db.Benchmark)
	for _, b := range g.benchmarks {
		if b.ID == "" {
			g.logger.Error("benchmark id should not be empty", zap.String("id", b.ID), zap.String("title", b.Title))
			continue
		}
		newBenchmarks[b.ID] = b
	}
	g.benchmarks = newBenchmarks

	var benchmarksStr []string
	for b := range g.benchmarks {
		benchmarksStr = append(benchmarksStr, b)
	}

	_ = g.fillBenchmarksIntegrationTypes(benchmarksStr)

	return nil
}

func (g *GitParser) HandleFrameworks(frameworks []Framework) error {
	benchmarkIntegrationTypes := make(map[string]map[string]bool)
	var childrenDfs func(framework db.Benchmark)
	childrenDfs = func(framework db.Benchmark) {
		if benchmarkIntegrationTypes[framework.ID] == nil {
			benchmarkIntegrationTypes[framework.ID] = make(map[string]bool)
		}
		for _, c := range framework.Controls {
			for _, it := range c.IntegrationType {
				benchmarkIntegrationTypes[framework.ID][it] = true
			}
			if c.Policy != nil {
				for _, it := range c.Policy.IntegrationType {
					benchmarkIntegrationTypes[framework.ID][it] = true
				}
			}
			if c.PolicyID != nil {
				if policy, ok := g.controlsPolicies[*c.PolicyID]; ok {
					for _, it := range policy.IntegrationType {
						benchmarkIntegrationTypes[framework.ID][it] = true
					}
				}
			}
		}
		for _, child := range framework.Children {
			childrenDfs(child)
			for it, _ := range benchmarkIntegrationTypes[child.ID] {
				benchmarkIntegrationTypes[framework.ID][it] = true
			}
		}
	}

	for _, f := range frameworks {
		err := g.HandleSingleFramework(f)
		if err != nil {
			return err
		}
	}

	for idx, benchmark := range g.benchmarks {
		for _, childID := range g.frameworksChildren[benchmark.ID] {
			for _, child := range g.benchmarks {
				if child.ID == childID {
					benchmark.Children = append(benchmark.Children, *child)
				}
			}
		}

		if len(g.frameworksChildren[benchmark.ID]) != len(benchmark.Children) {
			//fmt.Printf("could not find some benchmark children, %d != %d", len(children[benchmark.ID]), len(benchmark.Children))
		}
		g.benchmarks[idx] = benchmark
	}

	for _, f := range g.benchmarks {
		childrenDfs(*f)
	}
	for i, framework := range g.benchmarks {
		if it, ok := benchmarkIntegrationTypes[framework.ID]; ok {
			for k, _ := range it {
				g.benchmarks[i].IntegrationType = append(g.benchmarks[i].IntegrationType, k)
			}
		}
	}

	return nil
}

func (g *GitParser) HandleSingleFramework(framework Framework) error {
	var tags []db.BenchmarkTag

	tags = make([]db.BenchmarkTag, 0, len(framework.Tags))
	for tagKey, tagValue := range framework.Tags {
		tags = append(tags, db.BenchmarkTag{
			Tag: model.Tag{
				Key:   tagKey,
				Value: tagValue,
			},
			BenchmarkID: framework.ID,
		})
	}

	isBaseline := true
	enabled := false

	if framework.Defaults != nil {
		if framework.Defaults.IsBaseline != nil {
			isBaseline = *framework.Defaults.IsBaseline
		}

		enabled = framework.Defaults.Enabled
	}

	b := &db.Benchmark{
		ID:          framework.ID,
		Title:       framework.Title,
		DisplayCode: framework.SectionCode,
		Description: framework.Description,
		IsBaseline:  isBaseline,
		Enabled:     enabled,
		Tags:        tags,
		Children:    nil,
		Controls:    nil,
	}
	metadataJsonb := pgtype.JSONB{}
	err := metadataJsonb.Set([]byte(""))
	if err != nil {
		return err
	}
	b.Metadata = metadataJsonb

	for _, control := range g.controls {
		if contains(framework.Controls, control.ID) {
			b.Controls = append(b.Controls, control)
			g.frameworksControls[b.ID] = append(g.frameworksControls[b.ID], control.ID)
		}
	}

	for _, group := range framework.ControlGroup {
		if len(group.Controls) > 0 || len(group.ControlGroup) > 0 {
			err = g.HandleSingleFramework(group)
			if err != nil {
				return err
			}
		}
		g.frameworksChildren[framework.ID] = append(g.frameworksChildren[framework.ID], group.ID)
	}

	g.benchmarks[b.ID] = b
	return nil
}

func (g GitParser) fillBenchmarksIntegrationTypes(benchmarks []string) []string {
	integrationTypesMap := make(map[string]bool)

	for _, idx := range benchmarks {
		itsMap := make(map[string]bool)
		if len(g.frameworksChildren[idx]) > 0 {
			its := g.fillBenchmarksIntegrationTypes(g.frameworksChildren[idx])
			for _, it := range its {
				itsMap[it] = true
			}
		}
		for _, c := range g.benchmarks[idx].Controls {
			for _, it := range c.IntegrationType {
				itsMap[it] = true
			}
		}
		for _, it := range g.benchmarks[idx].IntegrationType {
			itsMap[it] = true
		}
		var newIntegrationTypes []string
		for it, _ := range itsMap {
			newIntegrationTypes = append(newIntegrationTypes, it)
		}
		g.benchmarks[idx].IntegrationType = newIntegrationTypes
		for _, c := range g.benchmarks[idx].IntegrationType {
			integrationTypesMap[c] = true
		}
	}

	var integrationTypes []string
	for it, _ := range integrationTypesMap {
		integrationTypes = append(integrationTypes, it)
	}

	return integrationTypes
}

func (g *GitParser) CheckForDuplicate() error {
	visited := map[string]bool{}
	for _, b := range g.benchmarks {
		if _, ok := visited[b.ID]; !ok {
			visited[b.ID] = true
		} else {
			return fmt.Errorf("duplicate benchmark id: %s", b.ID)
		}
	}
	return nil
}

func (g GitParser) ExtractBenchmarksMetadata() error {
	for i, b := range g.benchmarks {
		benchmarkControlsCache := make(map[string]BenchmarkControlsCache)
		controlsMap, err := getControlsUnderBenchmark(*b, benchmarkControlsCache)
		if err != nil {
			return err
		}
		benchmarkTablesCache := make(map[string]BenchmarkTablesCache)
		primaryTablesMap, listOfTablesMap, err := g.getTablesUnderBenchmark(*b, benchmarkTablesCache)
		if err != nil {
			return err
		}
		var listOfTables, primaryTables, controls []string
		for k, _ := range controlsMap {
			controls = append(controls, k)
		}
		for k, _ := range primaryTablesMap {
			primaryTables = append(primaryTables, k)
		}
		for k, _ := range listOfTablesMap {
			listOfTables = append(listOfTables, k)
		}
		metadata := db.BenchmarkMetadata{
			Controls:         controls,
			PrimaryResources: primaryTables,
			ListOfResources:  listOfTables,
		}
		metadataJson, err := json.Marshal(metadata)
		if err != nil {
			return err
		}
		metadataJsonb := pgtype.JSONB{}
		err = metadataJsonb.Set(metadataJson)
		if err != nil {
			return err
		}
		g.benchmarks[i].Metadata = metadataJsonb
	}
	return nil
}

func (g *GitParser) ExtractCompliance(compliancePath string, controlEnrichmentBasePath string) error {
	if err := g.ExtractParameters(); err != nil {
		return err
	}

	if err := g.ExtractPolicies(path.Join(compliancePath, "policies")); err != nil {
		return err
	}
	if err := g.ExtractControls(path.Join(compliancePath, "controls"), controlEnrichmentBasePath); err != nil {
		return err
	}
	if err := g.ExtractFrameworks(path.Join(compliancePath, "frameworks")); err != nil {
		return err
	}
	//if err := g.CheckForDuplicate(); err != nil {
	//	return err
	//}

	if err := g.ExtractBenchmarksMetadata(); err != nil {
		return err
	}
	return nil
}

func contains[T uint | int | string](arr []T, ob T) bool {
	for _, o := range arr {
		if o == ob {
			return true
		}
	}
	return false
}
