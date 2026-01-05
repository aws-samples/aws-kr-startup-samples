from aws_cdk import Stack, aws_kms as kms, aws_secretsmanager as secretsmanager
from constructs import Construct


class SecretsStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.kms_key = kms.Key(
            self,
            "ProxyKmsKey",
            alias="alias/claude-code-proxy",
            enable_key_rotation=True,
        )

        self.admin_credentials = secretsmanager.Secret(
            self,
            "AdminCredentials",
            secret_name="claude-code-proxy/admin-credentials",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "admin"}',
                generate_string_key="password",
            ),
        )

        self.key_hasher_secret = secretsmanager.Secret(
            self,
            "KeyHasherSecret",
            secret_name="claude-code-proxy/key-hasher-secret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                password_length=64, exclude_punctuation=True
            ),
        )

        self.jwt_secret = secretsmanager.Secret(
            self,
            "JwtSecret",
            secret_name="claude-code-proxy/jwt-secret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                password_length=64, exclude_punctuation=True
            ),
        )
