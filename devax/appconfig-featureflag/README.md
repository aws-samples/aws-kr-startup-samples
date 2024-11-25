# Code Recipe for AWS AppConfig

AWS AppConfig is a tool that enables safe and dynamic application configuration management. This service offers a significant advantage by allowing you to adjust application behavior in real time without redeploying code. In particular, the Feature Flag functionality is highly useful for deploying new features or controlling feature usage on a per-user basis.

With Feature Flags, for example, you can release a new feature to specific user groups (e.g., beta users) or enable the feature for a small percentage of total traffic to test its performance. Additionally, if an issue arises, the feature can be immediately disabled to minimize risk, allowing for rapid response.

AppConfig integrates with various environments, such as AWS Lambda, EC2, and container-based applications. It also provides SDKs and APIs to directly manage configuration values within your code. This makes it suitable for scenarios like feature releases, A/B testing, environment-specific configuration management, and urgent feature rollbacks.

When deploying this project, an AppConfig resource is created to define release flags and operational flags. Additionally, you can find code examples of a Lambda function utilizing these Feature Flags.


# How to deploy
1. Clone the repository
```
git clone https://github.com/aws-samples/aws-kr-startup-samples.git
cd devax/appconfig-featureflag
```

2. CDK Bootstrapping
```
cdk bootstrap
```
3. Deploy

```
cdk deploy
```
