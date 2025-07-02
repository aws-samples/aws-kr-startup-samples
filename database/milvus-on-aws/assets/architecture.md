# Milvus on AWS Architecture

Milvus is an open-source, cloud-native vector database designed for high-performance similarity search on massive vector datasets. Built on top of popular vector search libraries including Faiss, HNSW, DiskANN, and SCANN, it empowers AI applications and unstructured data retrieval scenarios.

## AWS Deployment Architecture

![Milvus Architecture](./milvus_architecture.png)

## Architectural Principles

Milvus follows the principle of **data plane and control plane disaggregation**, comprising four main layers that are mutually independent in terms of scalability and disaster recovery. This **shared-storage architecture** with fully disaggregated storage and compute layers enables:

- **Horizontal scaling** of compute nodes
- **Zero-disk WAL layer** for increased elasticity
- **Reduced operational overhead**
- **Separation of stream processing** (Streaming Node) and batch processing (Query Node and Data Node)

## Detailed Layer Architecture

### Layer 1: Access Layer (Stateless Proxies)
The access layer serves as the front layer of the system and endpoint to users:

**Components on AWS:**
- **Milvus Proxy Pods**: Deployed as Kubernetes pods in Amazon EKS
- **AWS Load Balancer Controller**: Provides unified service address and load balancing
- **Amazon EKS Ingress**: External access management

**Functions:**
- Validates client requests and reduces returned results
- Stateless design enables horizontal scaling
- Employs massively parallel processing (MPP) architecture
- Aggregates and post-processes intermediate results before returning final results

### Layer 2: Coordinator (The Brain)
The Coordinator serves as the brain of Milvus with exactly one active instance across the entire cluster:

**Responsibilities:**
- **DDL/DCL/TSO Management**: Handles data definition language (DDL) and data control language (DCL) requests
- **Streaming Service Management**: Binds WAL with Streaming Nodes and provides service discovery
- **Query Management**: Manages topology and load balancing for Query Nodes
- **Historical Data Management**: Distributes offline tasks to Data Nodes

**AWS Integration:**
- Deployed as a highly available pod in Amazon EKS
- Uses etcd (running in EKS) for cluster topology management
- Integrates with Amazon MSK for streaming service coordination

### Layer 3: Worker Nodes (Stateless Executors)
Worker nodes are stateless executors that follow instructions from the coordinator:

#### Streaming Node
- **Function**: Shard-level "mini-brain" providing shard-level consistency guarantees
- **Responsibilities**:
  - Growing data querying and query plan generation
  - Conversion of growing data into sealed (historical) data
  - Fault recovery based on underlying WAL storage
- **AWS Deployment**: Kubernetes pods with auto-scaling capabilities

#### Query Node
- **Function**: Loads historical data from object storage for querying
- **Responsibilities**:
  - Historical data querying
  - Loading sealed segments from Amazon S3
  - Vector similarity search execution
- **AWS Integration**: Direct integration with Amazon S3 for data retrieval

#### Data Node
- **Function**: Offline processing of historical data
- **Responsibilities**:
  - Data compaction
  - Index building
  - Segment management
- **AWS Integration**: Stores processed data and indexes in Amazon S3

### Layer 4: Storage (Data Persistence)
The storage layer is responsible for data persistence across three components:

#### Meta Storage (etcd)
- **Function**: Stores metadata snapshots and system state
- **Data Stored**:
  - Collection schemas
  - Message consumption checkpoints
  - Service registration and health check data
- **AWS Deployment**: Highly available etcd cluster in Amazon EKS
- **Requirements**: High availability, strong consistency, transaction support

#### WAL Storage (Amazon MSK)
- **Function**: Write-Ahead Log for data durability and consistency
- **Benefits**:
  - Cloud-native, zero-disk design
  - Scales effortlessly with demand
  - Simplified operations without local disk management
- **AWS Integration**: Amazon MSK (Managed Streaming for Apache Kafka)
- **Guarantees**: System-wide recovery and consistency mechanism

#### Object Storage (Amazon S3)
- **Function**: Stores persistent data files
- **Data Stored**:
  - Snapshot files of logs
  - Index files for scalar and vector data
  - Intermediate query results
  - Sealed segments
- **AWS Benefits**:
  - Cost-effective storage
  - High durability (99.999999999%)
  - Seamless scalability
  - Integration with AWS ecosystem

## API Categories and Data Flow

Milvus APIs are categorized by function and follow specific architectural paths:

| API Category | Operations | Example APIs | Architecture Flow |
|--------------|------------|--------------|-------------------|
| **DDL/DCL** | Schema & Access Control | `createCollection`, `dropCollection`, `hasCollection`, `createPartition` | Access Layer → Coordinator |
| **DML** | Data Manipulation | `insert`, `delete`, `upsert` | Access Layer → Streaming Worker Node |
| **DQL** | Data Query | `search`, `query` | Access Layer → Batch Worker Node (Query Nodes) |

### Example Data Flow: Vector Search Operation

1. **Client Request**: Client sends search request via SDK/RESTful API
2. **Load Balancing**: AWS Load Balancer routes request to available Proxy in Access Layer
3. **Request Validation**: Proxy validates request and forwards to Coordinator
4. **Query Routing**: Coordinator directs request to appropriate Query Nodes
5. **Data Loading**: Query Nodes load sealed segments from Amazon S3 as needed
6. **Vector Search**: Query Nodes perform similarity search using loaded indexes
7. **Result Aggregation**: Proxy aggregates results from multiple Query Nodes
8. **Response**: Final results returned to client through the same path

### Example Data Flow: Data Insertion

1. **Client Request**: Client sends insert request with vector data
2. **Access Layer**: Proxy validates and forwards request to Streaming Node
3. **WAL Logging**: Streaming Node logs operation to Amazon MSK for durability
4. **Real-time Processing**: Data is processed and made available for queries
5. **Segment Sealing**: When segments reach capacity, Streaming Node triggers conversion
6. **Batch Processing**: Data Node handles compaction and index building
7. **Storage**: Final data and indexes stored in Amazon S3

## AWS-Specific Benefits

### Scalability
- **EKS Auto Scaling**: Automatic scaling of worker nodes based on demand
- **MSK Scaling**: Managed Kafka scaling for WAL operations
- **S3 Unlimited Storage**: No storage capacity limitations

### High Availability
- **Multi-AZ Deployment**: Components distributed across availability zones
- **EKS Managed Control Plane**: AWS-managed Kubernetes control plane
- **MSK Multi-AZ**: Kafka brokers across multiple availability zones

### Cost Optimization
- **S3 Storage Classes**: Intelligent tiering for cost optimization
- **Spot Instances**: Cost-effective compute for non-critical workloads
- **Reserved Instances**: Predictable pricing for stable workloads

### Security
- **VPC Isolation**: Network-level security and isolation
- **IAM Integration**: Fine-grained access control
- **Encryption**: Data encryption at rest and in transit

## Performance Considerations

### Vector Search Optimization
- **Index Types**: Support for multiple index types (IVF, HNSW, etc.)
- **Memory Management**: Efficient memory usage with S3 caching
- **Parallel Processing**: MPP architecture for concurrent queries

### Storage Performance
- **S3 Transfer Acceleration**: Faster data transfer for global deployments
- **EBS Optimization**: High-performance storage for temporary data
- **Network Optimization**: Enhanced networking for EKS clusters

## Monitoring and Observability

### AWS Native Monitoring
- **CloudWatch Integration**: Metrics and logging for all components
- **EKS Monitoring**: Container insights and performance metrics
- **MSK Monitoring**: Kafka cluster health and performance
- **S3 Analytics**: Storage usage and access patterns

### Milvus-Specific Metrics
- **Query Performance**: Search latency and throughput metrics
- **Data Ingestion**: Insert rate and processing time
- **Resource Utilization**: CPU, memory, and storage usage per component

## Reference

- [Milvus Architecture Overview](https://milvus.io/docs/architecture_overview.md)
- [Amazon EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Amazon MSK Documentation](https://docs.aws.amazon.com/msk/)
- [Amazon S3 Documentation](https://docs.aws.amazon.com/s3/)