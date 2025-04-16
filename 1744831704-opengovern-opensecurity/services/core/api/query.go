package api

import (
	"bytes"
	"encoding/csv"
	"fmt"
	"time"
)

type QueryEngine string

const (
	QueryEngineCloudQL     = "cloudql"
	QueryEngineCloudQLRego = "cloudql-rego"
)

type RunQueryRequest struct {
	Page       Page                 `json:"page" validate:"required"`
	Query      *string              `json:"query"`
	UseCache   *bool                `json:"use_cache"`
	QueryId    *string              `json:"query_id"`
	AccountId  *string              `json:"account_id"`
	SourceId   *string              `json:"source_id"`
	ResultType *string              `json:"result_type"`
	Params     map[string]string    `json:"params"`
	Engine     *QueryEngine         `json:"engine"`
	Sorts      []NamedQuerySortItem `json:"sorts"`
}

type RunChatQueryRequest struct {
	ChatId string `json:"chat_id"`
}

type RunQueryResponse struct {
	Title   string   `json:"title"`   // Query Title
	Query   string   `json:"query"`   // Query
	Headers []string `json:"headers"` // Column names
	Result  [][]any  `json:"result"`  // Result of query. in order to access a specific cell please use Result[Row][Column]
}

func (qr *RunQueryResponse) ToCSV() (string, error) {
	var buf bytes.Buffer
	writer := csv.NewWriter(&buf)
	defer writer.Flush()

	// Write headers
	if err := writer.Write(qr.Headers); err != nil {
		return "", fmt.Errorf("failed to write headers: %w", err)
	}

	// Write result rows
	for _, row := range qr.Result {
		stringRow := make([]string, len(row))
		for i, cell := range row {
			stringRow[i] = fmt.Sprintf("%v", cell) // Convert any type to string
		}
		if err := writer.Write(stringRow); err != nil {
			return "", fmt.Errorf("failed to write row: %w", err)
		}
	}

	return buf.String(), nil
}

type NamedQueryHistory struct {
	Query      string    `json:"query"`
	ExecutedAt time.Time `json:"executed_at"`
}

type NamedQueryTagsResult struct {
	Key          string
	UniqueValues []string
}

type RunQueryByIDRequest struct {
	Page        Page                 `json:"page" validate:"required"`
	Type        string               `json:"type"`
	ID          string               `json:"id"`
	Sorts       []NamedQuerySortItem `json:"sorts"`
	QueryParams map[string]string    `json:"query_params"`
}

type ListQueriesFiltersResponse struct {
	Providers []string               `json:"providers"`
	Tags      []NamedQueryTagsResult `json:"tags"`
}

type GetAsyncQueryRunResultResponse struct {
	RunId       string           `json:"runID"`
	QueryID     string           `json:"queryID"`
	Parameters  []QueryParameter `json:"parameters"`
	ColumnNames []string         `json:"columnNames"`
	CreatedBy   string           `json:"createdBy"`
	TriggeredAt int64            `json:"triggeredAt"`
	EvaluatedAt int64            `json:"evaluatedAt"`
	Result      [][]string       `json:"result"`
}

type CachedEnabledQuery struct {
	QueryID string `json:"queryID"`
	LastRun time.Time
}

type AddQueryRequest struct {
	QueryID      string               `json:"query_id"`
	QueryName    string               `json:"query_name"`
	Query 	  string               `json:"query"`
	Description string               `json:"description"`
	Tags         []string             `json:"tags"`
	IntegrationTypes []string         `json:"integration_types"`
	Visibility   string               `json:"visibility"`
	Owner 	 string               `json:"owner"`
	IsBookmarked bool                 `json:"is_bookmarked"`

}