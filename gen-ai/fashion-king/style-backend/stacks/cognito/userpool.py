from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_cognito as cognito,
)
from constructs import Construct

class CognitoUserPoolStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.user_pool_name = self.node.try_get_context("cognito_user_pool_name") 
        self.client_name = self.node.try_get_context("cognito_client_name")
        self.domain_prefix = self.node.try_get_context("cognito_domain_prefix")
        
        self.user_pool = cognito.UserPool(
            self, 'AmazonBedrockGalleryUserPool',
            user_pool_name=self.user_pool_name,
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                username=True
            ),
            standard_attributes=cognito.StandardAttributes(
                fullname=cognito.StandardAttribute(
                    required=False,
                    mutable=True
                )
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
                temp_password_validity=Duration.days(7)
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        self.user_pool_client = cognito.UserPoolClient(
            self, 'AmazonBedrockGalleryUserPoolClient',
            user_pool=self.user_pool,
            user_pool_client_name=self.client_name,
            generate_secret=False,
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=True
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE,
                    cognito.OAuthScope.COGNITO_ADMIN
                ],
                callback_urls=[
                    "http://localhost:3000/callback",
                    "https://example.com/callback"
                ],
                logout_urls=[
                    "http://localhost:3000/logout",
                    "https://example.com/logout"
                ]
            )
        )
        
        CfnOutput(
            self, 'UserPoolId',
            value=self.user_pool.user_pool_id,
            description='ID of the Cognito User Pool'
        )
        
        CfnOutput(
            self, 'UserPoolClientId',
            value=self.user_pool_client.user_pool_client_id,
            description='ID of the Cognito User Pool Client'
        )