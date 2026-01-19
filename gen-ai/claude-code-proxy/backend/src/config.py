from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings
from functools import lru_cache
import json
import hashlib


def _load_secret_from_arn(arn: str) -> dict | str | None:
    """Load secret value from AWS Secrets Manager by ARN."""
    if not arn or not arn.startswith("arn:aws:secretsmanager:"):
        return None
    try:
        import boto3

        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=arn)
        secret_string = response.get("SecretString", "")
        # Try to parse as JSON, otherwise return as string
        try:
            return json.loads(secret_string)
        except json.JSONDecodeError:
            return secret_string
    except Exception:
        return None


def _load_database_url_from_arn(arn: str) -> str | None:
    """Load database URL from RDS secret ARN and construct connection string."""
    secret = _load_secret_from_arn(arn)
    if not secret or not isinstance(secret, dict):
        return None
    try:
        from urllib.parse import quote_plus

        username = secret.get("username", "postgres")
        password = quote_plus(secret.get("password", ""))  # URL encode password
        host = secret.get("host", "localhost")
        port = secret.get("port", 5432)
        dbname = secret.get("dbname", "postgres")
        return f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{dbname}"
    except Exception:
        return None


class Settings(BaseSettings):
    # Environment
    environment: str = "dev"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/proxy"
    database_url_arn: str = ""  # Optional: RDS secret ARN

    # Secrets (loaded from env or Secrets Manager)
    plan_api_key: str = ""
    plan_force_rate_limit: bool = False
    key_hasher_secret: str = ""
    key_hasher_secret_arn: str = ""  # Optional: Secrets Manager ARN
    jwt_secret: str = ""
    jwt_secret_arn: str = ""  # Optional: Secrets Manager ARN
    admin_username: str = "admin"
    admin_password_hash: str = ""
    admin_credentials_arn: str = ""  # Optional: Secrets Manager ARN for admin credentials

    # KMS
    kms_key_id: str = ""
    local_encryption_key: str = ""

    # Cache TTLs
    access_key_cache_ttl: int = 60
    bedrock_key_cache_ttl: int = 300
    budget_cache_ttl: int = 60

    # Circuit Breaker
    circuit_failure_threshold: int = 3
    circuit_failure_window: int = 60
    circuit_reset_timeout: int = 1800

    # Timeouts
    http_connect_timeout: float = 5.0
    http_read_timeout: float = 300.0

    # Claude Code client overrides
    claude_code_max_output_tokens: int = Field(
        default=4096,
        validation_alias=AliasChoices(
            "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "PROXY_CLAUDE_CODE_MAX_OUTPUT_TOKENS"
        ),
    )
    max_thinking_tokens: int = Field(
        default=1024,
        validation_alias=AliasChoices("MAX_THINKING_TOKENS", "PROXY_MAX_THINKING_TOKENS"),
    )

    # URLs
    plan_api_url: str = "https://api.anthropic.com"
    bedrock_region: str = "ap-northeast-2"
    bedrock_default_model: str = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    bedrock_model_mapping: dict[str, str] = {}
    plan_verify_ssl: bool = True
    plan_ca_bundle: str = ""

    # Internal: loaded admin password (plain text from Secrets Manager)
    _admin_password_plain: str = ""

    model_config = {"env_prefix": "PROXY_", "env_file": ".env"}

    def model_post_init(self, __context) -> None:
        """Load secrets from Secrets Manager ARNs after initialization."""
        # Load database URL from RDS secret ARN if not explicitly set
        if self.database_url_arn and (
            "database_url" not in self.model_fields_set or not self.database_url
        ):
            db_url = _load_database_url_from_arn(self.database_url_arn)
            if db_url:
                object.__setattr__(self, "database_url", db_url)

        # Load key hasher secret from ARN
        if self.key_hasher_secret_arn and not self.key_hasher_secret:
            secret = _load_secret_from_arn(self.key_hasher_secret_arn)
            if secret and isinstance(secret, str):
                object.__setattr__(self, "key_hasher_secret", secret)

        # Load JWT secret from ARN
        if self.jwt_secret_arn and not self.jwt_secret:
            secret = _load_secret_from_arn(self.jwt_secret_arn)
            if secret and isinstance(secret, str):
                object.__setattr__(self, "jwt_secret", secret)

        # Load admin credentials from ARN
        if self.admin_credentials_arn:
            creds = _load_secret_from_arn(self.admin_credentials_arn)
            if creds and isinstance(creds, dict):
                if "username" in creds:
                    object.__setattr__(self, "admin_username", creds["username"])
                if "password" in creds:
                    # Store plain password for comparison, also compute hash for backward compat
                    object.__setattr__(self, "_admin_password_plain", creds["password"])
                    password_hash = hashlib.sha256(creds["password"].encode()).hexdigest()
                    object.__setattr__(self, "admin_password_hash", password_hash)


@lru_cache
def get_settings() -> Settings:
    return Settings()
