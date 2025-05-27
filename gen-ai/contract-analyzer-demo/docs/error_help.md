### 일반적인 오류 및 해결 방법

**ValidationException: Invocation of model ID with on-demand throughput isn't supported**

- 원인: 현재 AWS Bedrock은 일부 모델에 대해 inference profile을 필요로 합니다.
- 해결: AWS Bedrock 콘솔에서 inference profile을 생성한 후, 해당 ID를 'Inference Profile ID' 필드에 입력하세요.

**ResourceNotFoundException: The specified model is currently unavailable**

- 원인: 선택한 모델이 현재 AWS 계정이나 리전에서 사용할 수 없습니다.
- 해결: 다른 모델을 선택하거나, AWS Bedrock 콘솔에서 모델 접근 권한을 확인하세요.

**AccessDeniedException: User is not authorized to perform bedrock:InvokeModel**

- 원인: AWS 자격 증명에 Bedrock 모델 호출 권한이 없습니다.
- 해결: AWS IAM에서 적절한 권한을 부여하세요. 