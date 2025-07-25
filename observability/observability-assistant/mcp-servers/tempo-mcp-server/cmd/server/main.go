package main

import (
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	"github.com/mark3labs/mcp-go/server"
	"github.com/scottlepp/tempo-mcp-server/internal/handlers"
)

const (
	version = "0.1.0"
)

func main() {
	// Create a new MCP server
	s := server.NewMCPServer(
		"Tempo MCP Server",
		version,
		server.WithResourceCapabilities(true, true),
		server.WithLogging(),
	)

	// Add Tempo tools
	tempoSearchTracesTool := handlers.NewSearchTracesTool()
	s.AddTool(tempoSearchTracesTool, handlers.HandleSearchTraces)

	tempoGetTraceByIDTool := handlers.NewGetTraceByIDTool()
	s.AddTool(tempoGetTraceByIDTool, handlers.HandleGetTraceByID)

	tempoSearchTagsTool := handlers.NewSearchTagsTool()
	s.AddTool(tempoSearchTagsTool, handlers.HandleSearchTags)

	tempoSearchTagValuesTool := handlers.NewSearchTagValuesTool()
	s.AddTool(tempoSearchTagValuesTool, handlers.HandleSearchTagValues)

	httpServer := server.NewStreamableHTTPServer(s)

	// Create a channel to handle shutdown signals
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)

	// Start HTTP server in a goroutine
	go func() {
		log.Printf("Starting HTTP server on http://localhost:8000")
		log.Printf("MCP Endpoint: http://localhost:8000/mcp")

		if err := httpServer.Start(":8000"); err != nil && err != http.ErrServerClosed {
			log.Fatalf("HTTP server error: %v", err)
		}
	}()

	// Wait for interrupt signal
	<-stop
	log.Println("Shutting down servers...")
}
