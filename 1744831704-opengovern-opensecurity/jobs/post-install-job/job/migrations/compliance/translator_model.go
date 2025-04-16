package compliance

import (
	"github.com/opengovern/og-util/pkg/integration"
	"github.com/opengovern/opensecurity/jobs/post-install-job/job/migrations/shared"
)

type Framework struct {
	ID          string `json:"id" yaml:"id"`
	Title       string `json:"title" yaml:"title"`
	Type        string `json:"type" yaml:"type"`
	Description string `json:"description" yaml:"description"`
	SectionCode string `json:"section-code" yaml:"section-code"`
	Defaults    *struct {
		IsBaseline        *bool `json:"is-baseline" yaml:"is-baseline"`
		Enabled           bool  `json:"enabled" yaml:"enabled"`
		TracksDriftEvents bool  `json:"tracks-drift-events" yaml:"tracks-drift-events"`
	} `json:"defaults"`
	Tags         map[string][]string `json:"tags" yaml:"tags"`
	ControlGroup []Framework         `json:"control-group" yaml:"control-group"`
	Controls     []string            `json:"controls" yaml:"controls"`
}

type Control struct {
	ID              string                    `json:"id" yaml:"id"`
	Title           string                    `json:"title" yaml:"title"`
	Type            string                    `json:"type" yaml:"type"`
	Description     string                    `json:"description" yaml:"description"`
	IntegrationType []string                  `json:"integration_type" yaml:"integration_type"`
	Parameters      []shared.ControlParameter `json:"parameters" yaml:"parameters"`
	Policy          *shared.Policy            `json:"policy" yaml:"policy"`
	Severity        string                    `json:"severity" yaml:"severity"`
	Tags            map[string][]string       `json:"tags" yaml:"tags"`
}

type NamedQuery struct {
	ID               string                    `json:"id" yaml:"id"`
	Title            string                    `json:"title" yaml:"title"`
	Description      string                    `json:"description" yaml:"description"`
	Parameters       []shared.ControlParameter `json:"parameters" yaml:"parameters"`
	IntegrationTypes []integration.Type        `json:"integration_type" yaml:"integration_type"`
	Query            string                    `json:"query" yaml:"query"`
	Tags             map[string][]string       `json:"tags" yaml:"tags"`
}
