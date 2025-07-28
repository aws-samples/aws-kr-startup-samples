package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
)

// Initialize a logger that writes to stderr instead of stdout
var logger = log.New(os.Stderr, "[tempo-mcp] ", log.LstdFlags)

// TempoResult represents the structure of Tempo query results
type TempoResult struct {
	Traces      []TempoTrace `json:"traces"`
	Metrics     interface{}  `json:"metrics,omitempty"`
	ErrorStatus string       `json:"error,omitempty"`
}

// TempoTrace represents a single trace in the result
type TempoTrace struct {
	TraceID           string            `json:"traceID"`
	RootServiceName   string            `json:"rootServiceName"`
	RootTraceName     string            `json:"rootTraceName"`
	StartTimeUnixNano string            `json:"startTimeUnixNano"`
	DurationMs        int64             `json:"durationMs"`
	SpanSet           interface{}       `json:"spanSet,omitempty"`
	Attributes        map[string]string `json:"attributes,omitempty"`
}

// TempoTraceResponse represents the response when querying a specific trace by ID
// The trace API returns the trace data directly, not wrapped in a response structure
type TempoTraceResponse struct {
	Batches []TempoBatch `json:"batches,omitempty"`
	// For error handling, we'll check HTTP status codes instead
}

// TempoBatch represents a batch of spans in the trace
type TempoBatch struct {
	Resource   TempoResource    `json:"resource,omitempty"`
	ScopeSpans []TempoScopeSpan `json:"scopeSpans,omitempty"`
}

// TempoResource represents resource attributes
type TempoResource struct {
	Attributes []TempoAttribute `json:"attributes,omitempty"`
}

// TempoScopeSpan represents a scope with its spans
type TempoScopeSpan struct {
	Scope TempoScope  `json:"scope,omitempty"`
	Spans []TempoSpan `json:"spans,omitempty"`
}

// TempoScope represents the instrumentation scope
type TempoScope struct {
	Name    string `json:"name,omitempty"`
	Version string `json:"version,omitempty"`
}

// TempoSpan represents a single span in the trace
type TempoSpan struct {
	TraceID           string           `json:"traceId,omitempty"`
	SpanID            string           `json:"spanId,omitempty"`
	ParentSpanID      string           `json:"parentSpanId,omitempty"`
	Name              string           `json:"name,omitempty"`
	Kind              string           `json:"kind,omitempty"`
	StartTimeUnixNano string           `json:"startTimeUnixNano,omitempty"`
	EndTimeUnixNano   string           `json:"endTimeUnixNano,omitempty"`
	Attributes        []TempoAttribute `json:"attributes,omitempty"`
	Events            []TempoEvent     `json:"events,omitempty"`
	Status            TempoStatus      `json:"status,omitempty"`
}

// TempoAttribute represents a key-value attribute
type TempoAttribute struct {
	Key   string     `json:"key,omitempty"`
	Value TempoValue `json:"value,omitempty"`
}

// TempoValue represents different types of attribute values
type TempoValue struct {
	StringValue string          `json:"stringValue,omitempty"`
	IntValue    interface{}     `json:"intValue,omitempty"` // Can be string or number
	ArrayValue  TempoArrayValue `json:"arrayValue,omitempty"`
}

// TempoArrayValue represents an array value
type TempoArrayValue struct {
	Values []TempoValue `json:"values,omitempty"`
}

// TempoEvent represents an event within a span
type TempoEvent struct {
	TimeUnixNano string           `json:"timeUnixNano,omitempty"`
	Name         string           `json:"name,omitempty"`
	Attributes   []TempoAttribute `json:"attributes,omitempty"`
}

// TempoStatus represents the status of a span
type TempoStatus struct {
	Code    string `json:"code,omitempty"`
	Message string `json:"message,omitempty"`
}

// TempoTagsResult represents the structure of Tempo tags search results
type TempoTagsResult struct {
	TagNames    []string    `json:"tagNames"`
	Metrics     interface{} `json:"metrics,omitempty"`
	ErrorStatus string      `json:"error,omitempty"`
}

// TempoTagValuesResult represents the structure of Tempo tag values search results
type TempoTagValuesResult struct {
	TagValues   []string    `json:"tagValues"`
	Metrics     interface{} `json:"metrics,omitempty"`
	ErrorStatus string      `json:"error,omitempty"`
}

// Environment variable name for Tempo URL
const EnvTempoURL = "TEMPO_URL"

// Environment variable names for authentication
const EnvTempoUsername = "TEMPO_USERNAME"
const EnvTempoPassword = "TEMPO_PASSWORD"
const EnvTempoToken = "TEMPO_TOKEN"

// Default Tempo URL when environment variable is not set
const DefaultTempoURL = "http://localhost:3200"

// NewSearchTracesTool creates and returns a tool for searching traces in Grafana Tempo
func NewSearchTracesTool() mcp.Tool {
	// Get Tempo URL from environment variable or use default
	tempoURL := os.Getenv(EnvTempoURL)
	if tempoURL == "" {
		tempoURL = DefaultTempoURL
	}

	return mcp.NewTool("search_traces",
		mcp.WithDescription("Search for traces in Grafana Tempo"),
		mcp.WithString("query",
			mcp.Required(),
			mcp.Description("Tempo trace search query string"),
		),
		mcp.WithString("url",
			mcp.Description(fmt.Sprintf("Tempo server URL (default: %s from %s env var)", tempoURL, EnvTempoURL)),
			mcp.DefaultString(tempoURL),
		),
		mcp.WithString("start",
			mcp.Description("Start time for the query (default: 1h ago)"),
		),
		mcp.WithString("end",
			mcp.Description("End time for the query (default: now)"),
		),
		mcp.WithNumber("limit",
			mcp.Description("Maximum number of traces to return (default: 20)"),
		),
	)
}

// NewGetTraceByIDTool creates and returns a tool for querying a specific trace by ID in Grafana Tempo
func NewGetTraceByIDTool() mcp.Tool {
	// Get Tempo URL from environment variable or use default
	tempoURL := os.Getenv(EnvTempoURL)
	if tempoURL == "" {
		tempoURL = DefaultTempoURL
	}

	return mcp.NewTool("get_trace_by_id",
		mcp.WithDescription("Retrieve a specific trace by its trace ID from Grafana Tempo"),
		mcp.WithString("traceID",
			mcp.Required(),
			mcp.Description("The trace ID to retrieve"),
		),
		mcp.WithString("url",
			mcp.Description(fmt.Sprintf("Tempo server URL (default: %s from %s env var)", tempoURL, EnvTempoURL)),
			mcp.DefaultString(tempoURL),
		),
		mcp.WithString("start",
			mcp.Description("Start time for the search (unix epoch seconds)"),
		),
		mcp.WithString("end",
			mcp.Description("End time for the search (unix epoch seconds)"),
		),
	)
}

// NewSearchTagsTool creates and returns a tool for searching available tags in Grafana Tempo
func NewSearchTagsTool() mcp.Tool {
	// Get Tempo URL from environment variable or use default
	tempoURL := os.Getenv(EnvTempoURL)
	if tempoURL == "" {
		tempoURL = DefaultTempoURL
	}

	return mcp.NewTool("search_tags",
		mcp.WithDescription("Search for available tag names in Grafana Tempo"),
		mcp.WithString("url",
			mcp.Description(fmt.Sprintf("Tempo server URL (default: %s from %s env var)", tempoURL, EnvTempoURL)),
			mcp.DefaultString(tempoURL),
		),
		mcp.WithString("scope",
			mcp.Description("Scope of the tags (resource|span|intrinsic). Default: all scopes"),
		),
		mcp.WithString("start",
			mcp.Description("Start time for the search (unix epoch seconds)"),
		),
		mcp.WithString("end",
			mcp.Description("End time for the search (unix epoch seconds)"),
		),
		mcp.WithNumber("limit",
			mcp.Description("Maximum number of tag values to return"),
		),
		mcp.WithNumber("maxStaleValues",
			mcp.Description("Limits the search for tag names. Search stops if this many stale values are found"),
		),
	)
}

// NewSearchTagValuesTool creates and returns a tool for searching tag values in Grafana Tempo
func NewSearchTagValuesTool() mcp.Tool {
	// Get Tempo URL from environment variable or use default
	tempoURL := os.Getenv(EnvTempoURL)
	if tempoURL == "" {
		tempoURL = DefaultTempoURL
	}

	return mcp.NewTool("search_tag_values",
		mcp.WithDescription("Search for values of a specific tag in Grafana Tempo"),
		mcp.WithString("tagName",
			mcp.Required(),
			mcp.Description("The tag name to search values for (e.g., 'service.name', 'http.method')"),
		),
		mcp.WithString("url",
			mcp.Description(fmt.Sprintf("Tempo server URL (default: %s from %s env var)", tempoURL, EnvTempoURL)),
			mcp.DefaultString(tempoURL),
		),
		mcp.WithString("start",
			mcp.Description("Start time for the search (unix epoch seconds)"),
		),
		mcp.WithString("end",
			mcp.Description("End time for the search (unix epoch seconds)"),
		),
		mcp.WithNumber("limit",
			mcp.Description("Maximum number of tag values to return"),
		),
		mcp.WithNumber("maxStaleValues",
			mcp.Description("Limits the search for tag values. Search stops if this many stale values are found"),
		),
	)
}

// HandleSearchTraces handles Tempo trace search tool requests
func HandleSearchTraces(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	// First type-assert the arguments to map[string]interface{}
	args, ok := request.Params.Arguments.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid arguments type")
	}

	// Extract parameters
	queryString, ok := args["query"].(string)
	if !ok {
		return nil, fmt.Errorf("query parameter is required and must be a string")
	}
	logger.Printf("Received Tempo trace search request: %s", queryString)

	// Get Tempo URL from request arguments, if not present check environment
	var tempoURL string
	if urlArg, ok := args["url"].(string); ok && urlArg != "" {
		tempoURL = urlArg
	} else {
		// Fallback to environment variable
		tempoURL = os.Getenv(EnvTempoURL)
		if tempoURL == "" {
			tempoURL = DefaultTempoURL
		}
	}
	logger.Printf("Using Tempo URL: %s", tempoURL)

	// Get authentication from environment variables
	username := os.Getenv(EnvTempoUsername)
	password := os.Getenv(EnvTempoPassword)
	token := os.Getenv(EnvTempoToken)

	// Set defaults for optional parameters
	start := time.Now().Add(-1 * time.Hour).Unix()
	end := time.Now().Unix()
	limit := 20

	// Override defaults if parameters are provided
	if startStr, ok := args["start"].(string); ok && startStr != "" {
		startTime, err := parseTime(startStr)
		if err != nil {
			return nil, fmt.Errorf("invalid start time: %v", err)
		}
		start = startTime.Unix()
	}

	if endStr, ok := args["end"].(string); ok && endStr != "" {
		endTime, err := parseTime(endStr)
		if err != nil {
			return nil, fmt.Errorf("invalid end time: %v", err)
		}
		end = endTime.Unix()
	}

	if limitVal, ok := args["limit"].(float64); ok {
		limit = int(limitVal)
	}

	logger.Printf("Search parameters - start: %d, end: %d, limit: %d", start, end, limit)

	// Build search URL
	searchURL, err := buildTempoSearchURL(tempoURL, queryString, start, end, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to build search URL: %v", err)
	}
	logger.Printf("Search URL: %s", searchURL)

	// Execute trace search with authentication
	result, err := executeTempoSearch(ctx, searchURL, username, password, token)
	if err != nil {
		logger.Printf("Search execution error: %v", err)
		return nil, fmt.Errorf("trace search failed: %v", err)
	}

	// Format text result
	formattedTextResult, err := formatTempoResults(result)
	if err != nil {
		return nil, fmt.Errorf("failed to format results: %v", err)
	}

	// Create result with text content - use the right format for the tool result
	toolResult := &mcp.CallToolResult{
		Content: []mcp.Content{
			mcp.TextContent{
				Type: "text",
				Text: formattedTextResult,
			},
		},
	}

	// Log summary to stderr
	logger.Printf("Search returned %d traces", len(result.Traces))

	return toolResult, nil
}

// HandleGetTraceByID handles Tempo trace retrieval by ID tool requests
func HandleGetTraceByID(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	// First type-assert the arguments to map[string]interface{}
	args, ok := request.Params.Arguments.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid arguments type")
	}

	// Extract required traceID parameter
	traceID, ok := args["traceID"].(string)
	if !ok || traceID == "" {
		return nil, fmt.Errorf("traceID parameter is required and must be a string")
	}
	logger.Printf("Received trace retrieval request for ID: %s", traceID)

	// Get Tempo URL from request arguments, if not present check environment
	var tempoURL string
	if urlArg, ok := args["url"].(string); ok && urlArg != "" {
		tempoURL = urlArg
	} else {
		// Fallback to environment variable
		tempoURL = os.Getenv(EnvTempoURL)
		if tempoURL == "" {
			tempoURL = DefaultTempoURL
		}
	}
	logger.Printf("Using Tempo URL: %s", tempoURL)

	// Get authentication from environment variables
	username := os.Getenv(EnvTempoUsername)
	password := os.Getenv(EnvTempoPassword)
	token := os.Getenv(EnvTempoToken)

	// Extract optional time parameters
	var start, end *int64
	if startStr, ok := args["start"].(string); ok && startStr != "" {
		startTime, err := parseTime(startStr)
		if err != nil {
			return nil, fmt.Errorf("invalid start time: %v", err)
		}
		startUnix := startTime.Unix()
		start = &startUnix
	}

	if endStr, ok := args["end"].(string); ok && endStr != "" {
		endTime, err := parseTime(endStr)
		if err != nil {
			return nil, fmt.Errorf("invalid end time: %v", err)
		}
		endUnix := endTime.Unix()
		end = &endUnix
	}

	// Build trace URL
	traceURL, err := buildTempoTraceURL(tempoURL, traceID, start, end)
	if err != nil {
		return nil, fmt.Errorf("failed to build trace URL: %v", err)
	}
	logger.Printf("Trace URL: %s", traceURL)

	// Execute trace retrieval with authentication
	result, err := executeTempoTraceQuery(ctx, traceURL, username, password, token)
	if err != nil {
		logger.Printf("Trace retrieval error: %v", err)
		return nil, fmt.Errorf("trace retrieval failed: %v", err)
	}

	// Format text result
	formattedTextResult, err := formatTraceResult(result)
	if err != nil {
		return nil, fmt.Errorf("failed to format trace result: %v", err)
	}

	// Create result with text content
	toolResult := &mcp.CallToolResult{
		Content: []mcp.Content{
			mcp.TextContent{
				Type: "text",
				Text: formattedTextResult,
			},
		},
	}

	logger.Printf("Trace retrieved successfully")
	return toolResult, nil
}

// HandleSearchTags handles Tempo tags search tool requests
func HandleSearchTags(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	// First type-assert the arguments to map[string]interface{}
	args, ok := request.Params.Arguments.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid arguments type")
	}

	logger.Printf("Received tags search request")

	// Get Tempo URL from request arguments, if not present check environment
	var tempoURL string
	if urlArg, ok := args["url"].(string); ok && urlArg != "" {
		tempoURL = urlArg
	} else {
		// Fallback to environment variable
		tempoURL = os.Getenv(EnvTempoURL)
		if tempoURL == "" {
			tempoURL = DefaultTempoURL
		}
	}
	logger.Printf("Using Tempo URL: %s", tempoURL)

	// Get authentication from environment variables
	username := os.Getenv(EnvTempoUsername)
	password := os.Getenv(EnvTempoPassword)
	token := os.Getenv(EnvTempoToken)

	// Extract optional parameters
	var scope string
	if scopeArg, ok := args["scope"].(string); ok {
		scope = scopeArg
	}

	var start, end *int64
	if startStr, ok := args["start"].(string); ok && startStr != "" {
		startTime, err := parseTime(startStr)
		if err != nil {
			return nil, fmt.Errorf("invalid start time: %v", err)
		}
		startUnix := startTime.Unix()
		start = &startUnix
	}

	if endStr, ok := args["end"].(string); ok && endStr != "" {
		endTime, err := parseTime(endStr)
		if err != nil {
			return nil, fmt.Errorf("invalid end time: %v", err)
		}
		endUnix := endTime.Unix()
		end = &endUnix
	}

	var limit, maxStaleValues *int
	if limitVal, ok := args["limit"].(float64); ok {
		limitInt := int(limitVal)
		limit = &limitInt
	}

	if maxStaleVal, ok := args["maxStaleValues"].(float64); ok {
		maxStaleInt := int(maxStaleVal)
		maxStaleValues = &maxStaleInt
	}

	// Build tags URL
	tagsURL, err := buildTempoTagsURL(tempoURL, scope, start, end, limit, maxStaleValues)
	if err != nil {
		return nil, fmt.Errorf("failed to build tags URL: %v", err)
	}
	logger.Printf("Tags URL: %s", tagsURL)

	// Execute tags search with authentication
	result, err := executeTempoTagsQuery(ctx, tagsURL, username, password, token)
	if err != nil {
		logger.Printf("Tags search error: %v", err)
		return nil, fmt.Errorf("tags search failed: %v", err)
	}

	// Format text result
	formattedTextResult, err := formatTagsResult(result)
	if err != nil {
		return nil, fmt.Errorf("failed to format tags result: %v", err)
	}

	// Create result with text content
	toolResult := &mcp.CallToolResult{
		Content: []mcp.Content{
			mcp.TextContent{
				Type: "text",
				Text: formattedTextResult,
			},
		},
	}

	logger.Printf("Tags search returned %d tag names", len(result.TagNames))
	return toolResult, nil
}

// HandleSearchTagValues handles Tempo tag values search tool requests
func HandleSearchTagValues(ctx context.Context, request mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	// First type-assert the arguments to map[string]interface{}
	args, ok := request.Params.Arguments.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("invalid arguments type")
	}

	// Extract required tagName parameter
	tagName, ok := args["tagName"].(string)
	if !ok || tagName == "" {
		return nil, fmt.Errorf("tagName parameter is required and must be a string")
	}
	logger.Printf("Received tag values search request for tag: %s", tagName)

	// Get Tempo URL from request arguments, if not present check environment
	var tempoURL string
	if urlArg, ok := args["url"].(string); ok && urlArg != "" {
		tempoURL = urlArg
	} else {
		// Fallback to environment variable
		tempoURL = os.Getenv(EnvTempoURL)
		if tempoURL == "" {
			tempoURL = DefaultTempoURL
		}
	}
	logger.Printf("Using Tempo URL: %s", tempoURL)

	// Get authentication from environment variables
	username := os.Getenv(EnvTempoUsername)
	password := os.Getenv(EnvTempoPassword)
	token := os.Getenv(EnvTempoToken)

	// Extract optional parameters
	var start, end *int64
	if startStr, ok := args["start"].(string); ok && startStr != "" {
		startTime, err := parseTime(startStr)
		if err != nil {
			return nil, fmt.Errorf("invalid start time: %v", err)
		}
		startUnix := startTime.Unix()
		start = &startUnix
	}

	if endStr, ok := args["end"].(string); ok && endStr != "" {
		endTime, err := parseTime(endStr)
		if err != nil {
			return nil, fmt.Errorf("invalid end time: %v", err)
		}
		endUnix := endTime.Unix()
		end = &endUnix
	}

	var limit, maxStaleValues *int
	if limitVal, ok := args["limit"].(float64); ok {
		limitInt := int(limitVal)
		limit = &limitInt
	}

	if maxStaleVal, ok := args["maxStaleValues"].(float64); ok {
		maxStaleInt := int(maxStaleVal)
		maxStaleValues = &maxStaleInt
	}

	// Build tag values URL
	tagValuesURL, err := buildTempoTagValuesURL(tempoURL, tagName, start, end, limit, maxStaleValues)
	if err != nil {
		return nil, fmt.Errorf("failed to build tag values URL: %v", err)
	}
	logger.Printf("Tag values URL: %s", tagValuesURL)

	// Execute tag values search with authentication
	result, err := executeTempoTagValuesQuery(ctx, tagValuesURL, username, password, token)
	if err != nil {
		logger.Printf("Tag values search error: %v", err)
		return nil, fmt.Errorf("tag values search failed: %v", err)
	}

	// Format text result
	formattedTextResult, err := formatTagValuesResult(result, tagName)
	if err != nil {
		return nil, fmt.Errorf("failed to format tag values result: %v", err)
	}

	// Create result with text content
	toolResult := &mcp.CallToolResult{
		Content: []mcp.Content{
			mcp.TextContent{
				Type: "text",
				Text: formattedTextResult,
			},
		},
	}

	logger.Printf("Tag values search returned %d values for tag '%s'", len(result.TagValues), tagName)
	return toolResult, nil
}

// parseTime converts a time string to a time.Time
func parseTime(timeStr string) (time.Time, error) {
	// Handle "now" keyword
	if timeStr == "now" {
		return time.Now(), nil
	}

	// Handle relative time strings like "-1h", "-30m"
	if len(timeStr) > 0 && timeStr[0] == '-' {
		duration, err := time.ParseDuration(timeStr)
		if err == nil {
			return time.Now().Add(duration), nil
		}
	}

	// Try parsing as RFC3339
	t, err := time.Parse(time.RFC3339, timeStr)
	if err == nil {
		return t, nil
	}

	// Try other common formats
	formats := []string{
		"2006-01-02T15:04:05",
		"2006-01-02 15:04:05",
		"2006-01-02",
	}

	for _, format := range formats {
		t, err := time.Parse(format, timeStr)
		if err == nil {
			return t, nil
		}
	}

	return time.Time{}, fmt.Errorf("unsupported time format: %s", timeStr)
}

// buildTempoSearchURL constructs the Tempo search URL
func buildTempoSearchURL(baseURL, query string, start, end int64, limit int) (string, error) {
	u, err := url.Parse(baseURL)
	if err != nil {
		return "", err
	}

	// Path for Tempo search API
	if !strings.Contains(u.Path, "/api/search") {
		if u.Path == "" || u.Path == "/" {
			u.Path = "/api/search"
		} else {
			u.Path = fmt.Sprintf("%s/api/search", u.Path)
		}
	}

	// Add search parameters
	q := u.Query()
	q.Set("q", query)

	// Just use Unix epoch seconds directly - no conversion needed
	// The API expects raw seconds since epoch
	q.Set("start", fmt.Sprintf("%d", start))
	q.Set("end", fmt.Sprintf("%d", end))
	q.Set("limit", fmt.Sprintf("%d", limit))
	u.RawQuery = q.Encode()

	return u.String(), nil
}

// executeTempoSearch sends the HTTP request to Tempo
func executeTempoSearch(ctx context.Context, searchURL, username, password, token string) (*TempoResult, error) {
	// Create HTTP request
	req, err := http.NewRequestWithContext(ctx, "GET", searchURL, nil)
	if err != nil {
		return nil, err
	}

	// Add authentication if provided
	if token != "" {
		// Bearer token authentication
		req.Header.Add("Authorization", "Bearer "+token)
	} else if username != "" || password != "" {
		// Basic authentication
		req.SetBasicAuth(username, password)
	}

	// Execute request
	client := &http.Client{
		Timeout: 30 * time.Second,
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	// Check for HTTP errors
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP error: %d - %s", resp.StatusCode, string(body))
	}

	// Log to stderr instead of stdout
	logger.Printf("Tempo raw response length: %d bytes", len(body))

	// Clean response if needed to ensure valid JSON
	cleanedBody := cleanTempoResponse(body)

	// Parse JSON response
	var result TempoResult
	if err := json.Unmarshal(cleanedBody, &result); err != nil {
		logger.Printf("ERROR parsing Tempo JSON response: %v", err)
		logger.Printf("Raw body: %s", string(cleanedBody)[:min(100, len(cleanedBody))])

		// Fall back to a more forgiving approach with generic JSON
		var genericResult map[string]interface{}
		genericErr := json.Unmarshal(cleanedBody, &genericResult)
		if genericErr != nil {
			// Return the original error if we can't even parse as generic JSON
			return nil, err
		}

		// Convert the generic result to our structured format
		convertedResult := &TempoResult{}

		// Try to extract traces array
		if tracesRaw, ok := genericResult["traces"]; ok {
			if tracesArr, ok := tracesRaw.([]interface{}); ok {
				for _, traceRaw := range tracesArr {
					if traceMap, ok := traceRaw.(map[string]interface{}); ok {
						trace := TempoTrace{}

						// Extract fields safely
						if id, ok := traceMap["traceID"].(string); ok {
							trace.TraceID = id
						}
						if svc, ok := traceMap["rootServiceName"].(string); ok {
							trace.RootServiceName = svc
						}
						if name, ok := traceMap["rootTraceName"].(string); ok {
							trace.RootTraceName = name
						}
						if start, ok := traceMap["startTimeUnixNano"].(string); ok {
							trace.StartTimeUnixNano = start
						}
						if dur, ok := traceMap["durationMs"].(float64); ok {
							trace.DurationMs = int64(dur)
						}

						// Add to result
						convertedResult.Traces = append(convertedResult.Traces, trace)
					}
				}
			}
		}

		// Extract error if present
		if errStatus, ok := genericResult["error"].(string); ok {
			convertedResult.ErrorStatus = errStatus
		}

		// Use the converted result
		result = *convertedResult
		logger.Printf("Used fallback JSON parsing for result")
	}

	logger.Printf("Tempo result parsed successfully: %d traces", len(result.Traces))

	// Check for Tempo errors
	if result.ErrorStatus != "" {
		return nil, fmt.Errorf("Tempo error: %s", result.ErrorStatus)
	}

	return &result, nil
}

// cleanTempoResponse cleans potentially problematic JSON from Tempo
func cleanTempoResponse(input []byte) []byte {
	// Convert to string for easier manipulation
	responseStr := string(input)

	// Check for common issues in Tempo's response
	if strings.HasSuffix(responseStr, "}]") {
		// This is likely a valid array ending
	} else if strings.HasSuffix(responseStr, "]}") {
		// This is likely a valid object ending
	} else if strings.Contains(responseStr, "}],") && strings.HasSuffix(responseStr, "}") {
		// This looks valid
	} else if strings.Contains(responseStr, "}]\"") {
		// Fix escaped quote issue by removing the escaped quotes
		responseStr = strings.Replace(responseStr, "}]\"", "}]", -1)
	} else if strings.Contains(responseStr, "}]}\"") {
		// Fix escaped quote issue
		responseStr = strings.Replace(responseStr, "}]}\"", "}]}", -1)
	}

	return []byte(responseStr)
}

// formatTempoResults formats the Tempo query results into a readable string
func formatTempoResults(result *TempoResult) (string, error) {
	logger.Printf("Formatting result with %d traces", len(result.Traces))

	if len(result.Traces) == 0 {
		// Log metrics data if present
		if result.Metrics != nil {
			logger.Printf("Metrics data: %+v", result.Metrics)
		}
		return "No traces found matching the search criteria", nil
	}

	var output strings.Builder
	output.WriteString(fmt.Sprintf("Found %d traces:\n\n", len(result.Traces)))

	for i, trace := range result.Traces {
		// Format trace information
		output.WriteString(fmt.Sprintf("Trace %d:\n", i+1))
		output.WriteString(fmt.Sprintf("  TraceID: %s\n", trace.TraceID))
		output.WriteString(fmt.Sprintf("  Service: %s\n", trace.RootServiceName))
		output.WriteString(fmt.Sprintf("  Name: %s\n", trace.RootTraceName))

		// Parse timestamp if available
		if trace.StartTimeUnixNano != "" {
			ts, err := strconv.ParseInt(trace.StartTimeUnixNano, 10, 64)
			if err == nil {
				timestamp := time.Unix(0, ts)
				output.WriteString(fmt.Sprintf("  Start Time: %s\n", timestamp.Format(time.RFC3339)))
			}
		}

		output.WriteString(fmt.Sprintf("  Duration: %d ms\n", trace.DurationMs))

		// Add attributes if available
		if len(trace.Attributes) > 0 {
			output.WriteString("  Attributes:\n")
			for k, v := range trace.Attributes {
				output.WriteString(fmt.Sprintf("    %s: %s\n", k, v))
			}
		}

		output.WriteString("\n")
	}

	// Get the formatted string but make sure we don't add a trailing newline that could mess up JSON
	formattedOutput := strings.TrimSuffix(output.String(), "\n")

	// Log to stderr
	logger.Printf("Formatted output length: %d chars", len(formattedOutput))
	return formattedOutput, nil
}

// buildTempoTraceURL constructs the Tempo trace retrieval URL
func buildTempoTraceURL(baseURL, traceID string, start, end *int64) (string, error) {
	u, err := url.Parse(baseURL)
	if err != nil {
		return "", err
	}

	// Path for Tempo traces API
	u.Path = fmt.Sprintf("/api/traces/%s", traceID)

	// Add query parameters if provided
	q := u.Query()
	if start != nil {
		q.Set("start", fmt.Sprintf("%d", *start))
	}
	if end != nil {
		q.Set("end", fmt.Sprintf("%d", *end))
	}
	u.RawQuery = q.Encode()

	return u.String(), nil
}

// buildTempoTagsURL constructs the Tempo tags search URL
func buildTempoTagsURL(baseURL, scope string, start, end *int64, limit, maxStaleValues *int) (string, error) {
	u, err := url.Parse(baseURL)
	if err != nil {
		return "", err
	}

	// Path for Tempo tags API
	if !strings.Contains(u.Path, "/api/search/tags") {
		if u.Path == "" || u.Path == "/" {
			u.Path = "/api/search/tags"
		} else {
			u.Path = fmt.Sprintf("%s/api/search/tags", u.Path)
		}
	}

	// Add query parameters
	q := u.Query()
	if scope != "" {
		q.Set("scope", scope)
	}
	if start != nil {
		q.Set("start", fmt.Sprintf("%d", *start))
	}
	if end != nil {
		q.Set("end", fmt.Sprintf("%d", *end))
	}
	if limit != nil {
		q.Set("limit", fmt.Sprintf("%d", *limit))
	}
	if maxStaleValues != nil {
		q.Set("maxStaleValues", fmt.Sprintf("%d", *maxStaleValues))
	}
	u.RawQuery = q.Encode()

	return u.String(), nil
}

// executeTempoTraceQuery sends the HTTP request to Tempo for trace retrieval
func executeTempoTraceQuery(ctx context.Context, traceURL, username, password, token string) (*TempoTraceResponse, error) {
	// Create HTTP request
	req, err := http.NewRequestWithContext(ctx, "GET", traceURL, nil)
	if err != nil {
		return nil, err
	}

	// Add authentication if provided
	if token != "" {
		// Bearer token authentication
		req.Header.Add("Authorization", "Bearer "+token)
	} else if username != "" || password != "" {
		// Basic authentication
		req.SetBasicAuth(username, password)
	}

	// Execute request
	client := &http.Client{
		Timeout: 30 * time.Second,
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	// Check for HTTP errors
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP error: %d - %s", resp.StatusCode, string(body))
	}

	logger.Printf("Tempo trace response length: %d bytes", len(body))

	// Parse JSON response
	var result TempoTraceResponse
	if err := json.Unmarshal(body, &result); err != nil {
		logger.Printf("ERROR parsing Tempo trace JSON response: %v", err)
		logger.Printf("Raw body: %s", string(body)[:min(200, len(body))])
		return nil, err
	}

	logger.Printf("Tempo trace result parsed successfully")

	// No need to check ErrorStatus since we're using HTTP status codes for error handling
	return &result, nil
}

// executeTempoTagsQuery sends the HTTP request to Tempo for tags search
func executeTempoTagsQuery(ctx context.Context, tagsURL, username, password, token string) (*TempoTagsResult, error) {
	// Create HTTP request
	req, err := http.NewRequestWithContext(ctx, "GET", tagsURL, nil)
	if err != nil {
		return nil, err
	}

	// Add authentication if provided
	if token != "" {
		// Bearer token authentication
		req.Header.Add("Authorization", "Bearer "+token)
	} else if username != "" || password != "" {
		// Basic authentication
		req.SetBasicAuth(username, password)
	}

	// Execute request
	client := &http.Client{
		Timeout: 30 * time.Second,
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	// Check for HTTP errors
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP error: %d - %s", resp.StatusCode, string(body))
	}

	logger.Printf("Tempo tags response length: %d bytes", len(body))

	// Parse JSON response
	var result TempoTagsResult
	if err := json.Unmarshal(body, &result); err != nil {
		logger.Printf("ERROR parsing Tempo tags JSON response: %v", err)
		logger.Printf("Raw body: %s", string(body)[:min(200, len(body))])
		return nil, err
	}

	logger.Printf("Tempo tags result parsed successfully")

	// Check for Tempo errors
	if result.ErrorStatus != "" {
		return nil, fmt.Errorf("Tempo error: %s", result.ErrorStatus)
	}

	return &result, nil
}

// formatTraceResult formats the Tempo trace result into a readable string
func formatTraceResult(result *TempoTraceResponse) (string, error) {
	logger.Printf("Formatting trace result")

	if len(result.Batches) == 0 {
		return "No trace found", nil
	}

	var output strings.Builder
	output.WriteString("Trace Details:\n\n")

	// Use the structured format with proper types
	if err := formatStructuredTrace(&output, result); err != nil {
		// Fallback to JSON on parsing error
		logger.Printf("Failed to parse structured format, falling back to JSON: %v", err)
		traceJSON, jsonErr := json.MarshalIndent(result, "", "  ")
		if jsonErr != nil {
			return "", fmt.Errorf("failed to marshal trace data: %v", jsonErr)
		}
		output.WriteString(string(traceJSON))
	}

	formattedOutput := strings.TrimSuffix(output.String(), "\n")
	logger.Printf("Formatted trace output length: %d chars", len(formattedOutput))
	return formattedOutput, nil
}

// formatStructuredTrace formats a structured TempoTraceResponse
func formatStructuredTrace(output *strings.Builder, result *TempoTraceResponse) error {
	var allSpans []TempoSpan
	var traceID string
	var serviceName string

	// Extract all spans from all batches
	for batchIdx, batch := range result.Batches {
		// Extract service name from resource attributes
		for _, attr := range batch.Resource.Attributes {
			if attr.Key == "service.name" && attr.Value.StringValue != "" {
				serviceName = attr.Value.StringValue
			}
		}

		// Extract spans from scopeSpans
		for _, scopeSpan := range batch.ScopeSpans {
			for _, span := range scopeSpan.Spans {
				// Extract trace ID from first span
				if traceID == "" && span.TraceID != "" {
					traceID = span.TraceID
				}
				allSpans = append(allSpans, span)
			}
		}

		if batchIdx == 0 {
			output.WriteString(fmt.Sprintf("Service: %s\n", serviceName))
			output.WriteString(fmt.Sprintf("Trace ID: %s\n", traceID))
			output.WriteString(fmt.Sprintf("Total Batches: %d\n\n", len(result.Batches)))
		}
	}

	// Format all spans
	if len(allSpans) > 0 {
		output.WriteString(fmt.Sprintf("Spans (%d total):\n\n", len(allSpans)))
		for i, span := range allSpans {
			formatStructuredSpan(output, span, i+1)
		}
	}

	return nil
}

// formatStructuredSpan formats a single structured TempoSpan
func formatStructuredSpan(output *strings.Builder, span TempoSpan, index int) {
	output.WriteString(fmt.Sprintf("Span %d:\n", index))

	// Basic span information
	if span.SpanID != "" {
		output.WriteString(fmt.Sprintf("  Span ID: %s\n", span.SpanID))
	}
	if span.ParentSpanID != "" {
		output.WriteString(fmt.Sprintf("  Parent Span ID: %s\n", span.ParentSpanID))
	}
	if span.Name != "" {
		output.WriteString(fmt.Sprintf("  Name: %s\n", span.Name))
	}
	if span.Kind != "" {
		output.WriteString(fmt.Sprintf("  Kind: %s\n", span.Kind))
	}

	// Timestamps
	if span.StartTimeUnixNano != "" {
		if startNano, err := strconv.ParseInt(span.StartTimeUnixNano, 10, 64); err == nil {
			startTimestamp := time.Unix(0, startNano)
			output.WriteString(fmt.Sprintf("  Start Time: %s\n", startTimestamp.Format(time.RFC3339Nano)))
		}
	}
	if span.EndTimeUnixNano != "" {
		if endNano, err := strconv.ParseInt(span.EndTimeUnixNano, 10, 64); err == nil {
			endTimestamp := time.Unix(0, endNano)
			output.WriteString(fmt.Sprintf("  End Time: %s\n", endTimestamp.Format(time.RFC3339Nano)))
		}
	}

	// Calculate duration
	if span.StartTimeUnixNano != "" && span.EndTimeUnixNano != "" {
		if startNano, err1 := strconv.ParseInt(span.StartTimeUnixNano, 10, 64); err1 == nil {
			if endNano, err2 := strconv.ParseInt(span.EndTimeUnixNano, 10, 64); err2 == nil {
				durationNano := endNano - startNano
				duration := time.Duration(durationNano)
				output.WriteString(fmt.Sprintf("  Duration: %s\n", duration.String()))
			}
		}
	}

	// Attributes
	if len(span.Attributes) > 0 {
		output.WriteString("  Attributes:\n")
		for _, attr := range span.Attributes {
			if attr.Value.StringValue != "" {
				output.WriteString(fmt.Sprintf("    %s: %s\n", attr.Key, attr.Value.StringValue))
			} else if attr.Value.IntValue != nil {
				output.WriteString(fmt.Sprintf("    %s: %v\n", attr.Key, attr.Value.IntValue))
			}
		}
	}

	// Events
	if len(span.Events) > 0 {
		output.WriteString("  Events:\n")
		for _, event := range span.Events {
			if event.Name != "" {
				output.WriteString(fmt.Sprintf("    Event: %s\n", event.Name))
			}
			if event.TimeUnixNano != "" {
				if eventNano, err := strconv.ParseInt(event.TimeUnixNano, 10, 64); err == nil {
					eventTimestamp := time.Unix(0, eventNano)
					output.WriteString(fmt.Sprintf("      Time: %s\n", eventTimestamp.Format(time.RFC3339Nano)))
				}
			}
			for _, attr := range event.Attributes {
				if attr.Value.StringValue != "" {
					output.WriteString(fmt.Sprintf("      %s: %s\n", attr.Key, attr.Value.StringValue))
				} else if attr.Value.IntValue != nil {
					output.WriteString(fmt.Sprintf("      %s: %v\n", attr.Key, attr.Value.IntValue))
				}
			}
		}
	}

	output.WriteString("\n")
}

// formatOpenTelemetryTrace formats an OpenTelemetry trace structure
func formatOpenTelemetryTrace(output *strings.Builder, traceData map[string]interface{}) error {
	// Check if this is a batches-based structure
	if batches, ok := traceData["batches"].([]interface{}); ok {
		return formatBatchedTrace(output, batches)
	}

	// Check if this is a direct spans structure
	if spans, ok := traceData["spans"].([]interface{}); ok {
		return formatDirectSpans(output, spans, nil)
	}

	// If we can't recognize the structure, return an error to fallback to JSON
	return fmt.Errorf("unrecognized trace structure")
}

// formatBatchedTrace formats a trace with batches structure
func formatBatchedTrace(output *strings.Builder, batches []interface{}) error {
	var allSpans []map[string]interface{}
	var traceID string
	var serviceName string

	// Extract all spans from all batches
	for batchIdx, batch := range batches {
		batchMap, ok := batch.(map[string]interface{})
		if !ok {
			continue
		}

		// Extract resource information
		if resource, ok := batchMap["resource"].(map[string]interface{}); ok {
			if attributes, ok := resource["attributes"].([]interface{}); ok {
				for _, attr := range attributes {
					if attrMap, ok := attr.(map[string]interface{}); ok {
						if key, ok := attrMap["key"].(string); ok && key == "service.name" {
							if value, ok := attrMap["value"].(map[string]interface{}); ok {
								if stringValue, ok := value["stringValue"].(string); ok {
									serviceName = stringValue
								}
							}
						}
					}
				}
			}
		}

		// Extract spans from scopeSpans
		if scopeSpans, ok := batchMap["scopeSpans"].([]interface{}); ok {
			for _, scopeSpan := range scopeSpans {
				if scopeSpanMap, ok := scopeSpan.(map[string]interface{}); ok {
					if spans, ok := scopeSpanMap["spans"].([]interface{}); ok {
						for _, span := range spans {
							if spanMap, ok := span.(map[string]interface{}); ok {
								// Extract trace ID from first span
								if traceID == "" {
									if tid, ok := spanMap["traceId"].(string); ok {
										traceID = tid
									}
								}
								allSpans = append(allSpans, spanMap)
							}
						}
					}
				}
			}
		}

		if batchIdx == 0 {
			output.WriteString(fmt.Sprintf("Service: %s\n", serviceName))
			output.WriteString(fmt.Sprintf("Trace ID: %s\n", traceID))
			output.WriteString(fmt.Sprintf("Total Batches: %d\n\n", len(batches)))
		}
	}

	// Format all spans
	if len(allSpans) > 0 {
		output.WriteString(fmt.Sprintf("Spans (%d total):\n\n", len(allSpans)))
		for i, span := range allSpans {
			formatSingleSpan(output, span, i+1)
		}
	}

	return nil
}

// formatDirectSpans formats spans that are directly in the trace
func formatDirectSpans(output *strings.Builder, spans []interface{}, resource map[string]interface{}) error {
	output.WriteString(fmt.Sprintf("Spans (%d total):\n\n", len(spans)))

	for i, span := range spans {
		if spanMap, ok := span.(map[string]interface{}); ok {
			formatSingleSpan(output, spanMap, i+1)
		}
	}

	return nil
}

// formatSingleSpan formats a single span
func formatSingleSpan(output *strings.Builder, span map[string]interface{}, index int) {
	output.WriteString(fmt.Sprintf("Span %d:\n", index))

	// Basic span information
	if spanId, ok := span["spanId"].(string); ok {
		output.WriteString(fmt.Sprintf("  Span ID: %s\n", spanId))
	}
	if parentSpanId, ok := span["parentSpanId"].(string); ok {
		output.WriteString(fmt.Sprintf("  Parent Span ID: %s\n", parentSpanId))
	}
	if name, ok := span["name"].(string); ok {
		output.WriteString(fmt.Sprintf("  Name: %s\n", name))
	}
	if kind, ok := span["kind"].(string); ok {
		output.WriteString(fmt.Sprintf("  Kind: %s\n", kind))
	}

	// Timestamps
	if startTime, ok := span["startTimeUnixNano"].(string); ok {
		if startNano, err := strconv.ParseInt(startTime, 10, 64); err == nil {
			startTimestamp := time.Unix(0, startNano)
			output.WriteString(fmt.Sprintf("  Start Time: %s\n", startTimestamp.Format(time.RFC3339Nano)))
		}
	}
	if endTime, ok := span["endTimeUnixNano"].(string); ok {
		if endNano, err := strconv.ParseInt(endTime, 10, 64); err == nil {
			endTimestamp := time.Unix(0, endNano)
			output.WriteString(fmt.Sprintf("  End Time: %s\n", endTimestamp.Format(time.RFC3339Nano)))
		}
	}

	// Calculate duration
	if startTime, ok1 := span["startTimeUnixNano"].(string); ok1 {
		if endTime, ok2 := span["endTimeUnixNano"].(string); ok2 {
			if startNano, err1 := strconv.ParseInt(startTime, 10, 64); err1 == nil {
				if endNano, err2 := strconv.ParseInt(endTime, 10, 64); err2 == nil {
					durationNano := endNano - startNano
					duration := time.Duration(durationNano)
					output.WriteString(fmt.Sprintf("  Duration: %s\n", duration.String()))
				}
			}
		}
	}

	// Attributes
	if attributes, ok := span["attributes"].([]interface{}); ok && len(attributes) > 0 {
		output.WriteString("  Attributes:\n")
		for _, attr := range attributes {
			if attrMap, ok := attr.(map[string]interface{}); ok {
				if key, ok := attrMap["key"].(string); ok {
					if value, ok := attrMap["value"].(map[string]interface{}); ok {
						if stringValue, ok := value["stringValue"].(string); ok {
							output.WriteString(fmt.Sprintf("    %s: %s\n", key, stringValue))
						} else if intValue, ok := value["intValue"].(string); ok {
							output.WriteString(fmt.Sprintf("    %s: %s\n", key, intValue))
						} else if intValue, ok := value["intValue"].(float64); ok {
							output.WriteString(fmt.Sprintf("    %s: %.0f\n", key, intValue))
						}
					}
				}
			}
		}
	}

	// Events
	if events, ok := span["events"].([]interface{}); ok && len(events) > 0 {
		output.WriteString("  Events:\n")
		for _, event := range events {
			if eventMap, ok := event.(map[string]interface{}); ok {
				if name, ok := eventMap["name"].(string); ok {
					output.WriteString(fmt.Sprintf("    Event: %s\n", name))
				}
				if timeUnixNano, ok := eventMap["timeUnixNano"].(string); ok {
					if eventNano, err := strconv.ParseInt(timeUnixNano, 10, 64); err == nil {
						eventTimestamp := time.Unix(0, eventNano)
						output.WriteString(fmt.Sprintf("      Time: %s\n", eventTimestamp.Format(time.RFC3339Nano)))
					}
				}
				if attributes, ok := eventMap["attributes"].([]interface{}); ok {
					for _, attr := range attributes {
						if attrMap, ok := attr.(map[string]interface{}); ok {
							if key, ok := attrMap["key"].(string); ok {
								if value, ok := attrMap["value"].(map[string]interface{}); ok {
									if stringValue, ok := value["stringValue"].(string); ok {
										output.WriteString(fmt.Sprintf("      %s: %s\n", key, stringValue))
									} else if intValue, ok := value["intValue"].(string); ok {
										output.WriteString(fmt.Sprintf("      %s: %s\n", key, intValue))
									} else if intValue, ok := value["intValue"].(float64); ok {
										output.WriteString(fmt.Sprintf("      %s: %.0f\n", key, intValue))
									}
								}
							}
						}
					}
				}
			}
		}
	}

	output.WriteString("\n")
}

// formatTagsResult formats the Tempo tags result into a readable string
func formatTagsResult(result *TempoTagsResult) (string, error) {
	logger.Printf("Formatting tags result with %d tag names", len(result.TagNames))

	if len(result.TagNames) == 0 {
		return "No tag names found", nil
	}

	var output strings.Builder
	output.WriteString(fmt.Sprintf("Found %d tag names:\n\n", len(result.TagNames)))

	for i, tagName := range result.TagNames {
		output.WriteString(fmt.Sprintf("%d. %s\n", i+1, tagName))
	}

	// Add metrics if available
	if result.Metrics != nil {
		output.WriteString("\nMetrics:\n")
		metricsJSON, err := json.MarshalIndent(result.Metrics, "", "  ")
		if err == nil {
			output.WriteString(string(metricsJSON))
		}
	}

	formattedOutput := strings.TrimSuffix(output.String(), "\n")
	logger.Printf("Formatted tags output length: %d chars", len(formattedOutput))
	return formattedOutput, nil
}

// buildTempoTagValuesURL constructs the Tempo tag values search URL
func buildTempoTagValuesURL(baseURL, tagName string, start, end *int64, limit, maxStaleValues *int) (string, error) {
	u, err := url.Parse(baseURL)
	if err != nil {
		return "", err
	}

	// Path for Tempo tag values API
	u.Path = fmt.Sprintf("/api/search/tag/%s/values", tagName)

	// Add query parameters
	q := u.Query()
	if start != nil {
		q.Set("start", fmt.Sprintf("%d", *start))
	}
	if end != nil {
		q.Set("end", fmt.Sprintf("%d", *end))
	}
	if limit != nil {
		q.Set("limit", fmt.Sprintf("%d", *limit))
	}
	if maxStaleValues != nil {
		q.Set("maxStaleValues", fmt.Sprintf("%d", *maxStaleValues))
	}
	u.RawQuery = q.Encode()

	return u.String(), nil
}

// executeTempoTagValuesQuery sends the HTTP request to Tempo for tag values search
func executeTempoTagValuesQuery(ctx context.Context, tagValuesURL, username, password, token string) (*TempoTagValuesResult, error) {
	// Create HTTP request
	req, err := http.NewRequestWithContext(ctx, "GET", tagValuesURL, nil)
	if err != nil {
		return nil, err
	}

	// Add authentication if provided
	if token != "" {
		// Bearer token authentication
		req.Header.Add("Authorization", "Bearer "+token)
	} else if username != "" || password != "" {
		// Basic authentication
		req.SetBasicAuth(username, password)
	}

	// Execute request
	client := &http.Client{
		Timeout: 30 * time.Second,
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	// Check for HTTP errors
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP error: %d - %s", resp.StatusCode, string(body))
	}

	logger.Printf("Tempo tag values response length: %d bytes", len(body))

	// Parse JSON response
	var result TempoTagValuesResult
	if err := json.Unmarshal(body, &result); err != nil {
		logger.Printf("ERROR parsing Tempo tag values JSON response: %v", err)
		logger.Printf("Raw body: %s", string(body)[:min(200, len(body))])
		return nil, err
	}

	logger.Printf("Tempo tag values result parsed successfully")

	// Check for Tempo errors
	if result.ErrorStatus != "" {
		return nil, fmt.Errorf("Tempo error: %s", result.ErrorStatus)
	}

	return &result, nil
}

// formatTagValuesResult formats the Tempo tag values result into a readable string
func formatTagValuesResult(result *TempoTagValuesResult, tagName string) (string, error) {
	logger.Printf("Formatting tag values result with %d values for tag '%s'", len(result.TagValues), tagName)

	if len(result.TagValues) == 0 {
		return fmt.Sprintf("No values found for tag '%s'", tagName), nil
	}

	var output strings.Builder
	output.WriteString(fmt.Sprintf("Found %d values for tag '%s':\n\n", len(result.TagValues), tagName))

	for i, tagValue := range result.TagValues {
		output.WriteString(fmt.Sprintf("%d. %s\n", i+1, tagValue))
	}

	// Add metrics if available
	if result.Metrics != nil {
		output.WriteString("\nMetrics:\n")
		metricsJSON, err := json.MarshalIndent(result.Metrics, "", "  ")
		if err == nil {
			output.WriteString(string(metricsJSON))
		}
	}

	formattedOutput := strings.TrimSuffix(output.String(), "\n")
	logger.Printf("Formatted tag values output length: %d chars", len(formattedOutput))
	return formattedOutput, nil
}

// min returns the minimum of two integers
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
