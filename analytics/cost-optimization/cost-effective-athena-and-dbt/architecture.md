```mermaid
graph TB
    %% User/Client
    User[👤 User] --> LB[🌐 Internet Gateway]

    %% VPC Structure
    subgraph VPC["🏢 Workshop VPC (10.0.0.0/16)"]
        %% Public Subnets
        subgraph PublicZone["🌍 Public Subnets"]
            PubSub1[Public Subnet 1<br/>10.0.3.0/24]
            PubSub2[Public Subnet 2<br/>10.0.4.0/24]
            PubSub3[Public Subnet 3<br/>10.0.5.0/24]
            NAT[🔄 NAT Gateway]
        end

        %% Private Subnets
        subgraph PrivateZone["🔒 Private Subnets"]
            PrivSub1[Private Subnet 1<br/>10.0.0.0/24]
            PrivSub2[Private Subnet 2<br/>10.0.1.0/24]
            PrivSub3[Private Subnet 3<br/>10.0.2.0/24]
        end

        %% Database Layer
        subgraph DatabaseLayer["💾 Database Layer"]
            Aurora[(🗄️ Aurora MySQL<br/>Writer + Reader<br/>dbt-athena-aurora-cluster)]
            Secrets[🔐 Secrets Manager<br/>DB Credentials]
        end

        %% Compute Layer
        subgraph ComputeLayer["⚡ Compute Layer"]
            Lambda[🔧 Sales Generator Lambda<br/>Every 2 minutes<br/>Generate sample data]
            LambdaSG[🛡️ Lambda Security Group]
        end
    end

    %% Storage Layer
    subgraph StorageLayer["📦 Storage Layer"]
        S3DataLake[🪣 S3 Data Lake<br/>athena-data-lake-bucket<br/>Raw Data Storage]
        S3Canary[🪣 S3 Canary Artifacts<br/>cid-canary-bucket<br/>Synthetics Results]
    end

    %% Data Processing Layer
    subgraph DataProcessing["🔄 Data Processing"]
        DMS[📡 DMS Serverless<br/>MySQL → S3<br/>Full Load + CDC]
        Glue[(🕷️ AWS Glue)]
        GlueDB[📊 Glue Database<br/>raw_data]
        GlueCrawler[🔍 Glue Crawler<br/>TicketCrawler]
    end

    %% Monitoring Layer
    subgraph MonitoringLayer["📊 Monitoring"]
        Synthetics[🔍 CloudWatch Synthetics<br/>create-more-spice<br/>Health Check Canary]
        EventBridge[⏰ EventBridge<br/>Lambda Trigger<br/>Rate: 2 minutes]
    end

    %% Connections
    LB --> PubSub1
    PubSub1 --> NAT
    NAT --> PrivSub1
    NAT --> PrivSub2
    NAT --> PrivSub3

    %% Database Connections
    PrivSub1 --> Aurora
    PrivSub2 --> Aurora
    PrivSub3 --> Aurora
    Aurora --> Secrets

    %% Lambda Connections
    Lambda --> Aurora
    Lambda --> Secrets
    EventBridge --> Lambda
    Lambda --> LambdaSG

    %% DMS Connections
    DMS --> Aurora
    DMS --> S3DataLake
    DMS --> Secrets

    %% Glue Connections
    GlueCrawler --> S3DataLake
    GlueCrawler --> GlueDB
    Glue --> GlueDB

    %% Synthetics Connections
    Synthetics --> S3Canary

    %% Data Flow
    Aurora -.->|DMS Replication| S3DataLake
    S3DataLake -.->|Crawl & Catalog| GlueCrawler
    GlueCrawler -.->|Create Tables| GlueDB

    %% Styling
    classDef vpc fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef database fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef storage fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef compute fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef monitoring fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef processing fill:#f1f8e9,stroke:#33691e,stroke-width:2px

    class VPC,PublicZone,PrivateZone vpc
    class DatabaseLayer,Aurora,Secrets database
    class StorageLayer,S3DataLake,S3Canary storage
    class ComputeLayer,Lambda,LambdaSG compute
    class MonitoringLayer,Synthetics,EventBridge monitoring
    class DataProcessing,DMS,Glue,GlueDB,GlueCrawler processing
    ```