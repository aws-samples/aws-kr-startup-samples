import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct
from cdklabs import generative_ai_cdk_constructs as genai

class KnowledgeBaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 버킷 생성
        self.bucket = s3.Bucket(self, "KnowledgeBaseBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # assets/novel 디렉토리의 파일들을 S3 버킷에 업로드
        self.upload_novel_files()

        # Knowledge Base 생성
        kb = genai.bedrock.KnowledgeBase(self, 'KnowledgeBase',
            embeddings_model=genai.bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V1
        )

        # S3 데이터 소스 추가
        data_source = genai.bedrock.S3DataSource(self, 'S3DataSource',
            bucket=self.bucket,
            data_source_name="ChatbotDataSource",
            knowledge_base=kb
        )

        # 출력
        CfnOutput(self, 'KnowledgeBaseId', value=kb.knowledge_base_id, export_name='KnowledgeBaseId')
        CfnOutput(self, 'KnowledgeBaseName', value=kb.knowledge_base_arn)
        CfnOutput(self, 'S3BucketName', value=self.bucket.bucket_name)

        self.knowledge_base_id = kb.knowledge_base_id

    def upload_novel_files(self):
        return s3deploy.BucketDeployment(
            self, 
            "UploadNovelFiles", 
            sources=[s3deploy.Source.asset("./assets/novel")],
            destination_bucket=self.bucket,
            destination_key_prefix="novels"
        )