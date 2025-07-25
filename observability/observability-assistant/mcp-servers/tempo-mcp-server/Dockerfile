FROM golang:1.24-alpine AS builder

WORKDIR /app

# Copy go mod files first for better caching
COPY go.mod go.sum* ./
RUN go env -w GOPROXY=direct
RUN apk add --no-cache git
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o tempo-mcp-server ./cmd/server

# Use a minimal Alpine image for the final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copy the binary from the builder stage
COPY --from=builder /app/tempo-mcp-server .

# Expose the default port for SSE server
EXPOSE 8000

# Set the entrypoint
ENTRYPOINT ["./tempo-mcp-server"] 