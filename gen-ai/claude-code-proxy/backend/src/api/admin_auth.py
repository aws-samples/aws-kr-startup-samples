from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from jose import jwt
import secrets
import hashlib

from ..config import get_settings

router = APIRouter(prefix="/admin/auth", tags=["auth"])
security = HTTPBasic()

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _get_jwt_secret() -> str:
    settings = get_settings()
    return settings.jwt_secret or secrets.token_hex(32)


def verify_admin(credentials: HTTPBasicCredentials) -> bool:
    settings = get_settings()
    username_correct = secrets.compare_digest(credentials.username, settings.admin_username)

    # Hash provided password and compare
    provided_hash = hashlib.sha256(credentials.password.encode()).hexdigest()
    password_correct = secrets.compare_digest(provided_hash, settings.admin_password_hash)

    return username_correct and password_correct


def create_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, _get_jwt_secret(), algorithm=ALGORITHM)


def verify_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.JWTError:
        return None


@router.post("/login", response_model=TokenResponse)
async def login(credentials: HTTPBasicCredentials = Depends(security)):
    if not verify_admin(credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    token = create_token(credentials.username)
    return TokenResponse(access_token=token)
