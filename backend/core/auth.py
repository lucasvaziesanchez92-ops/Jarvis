"""Authentication and authorization module with JWT support."""
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.config import settings

# ── Configuration ──────────────────────────────────────────────

# In production, set these via environment variables
SECRET_KEY = getattr(settings, "jwt_secret_key", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ── Password Hashing ──────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


# ── Token Models ──────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str  # user_id
    exp: datetime
    type: str  # "access" or "refresh"


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


# ── Password Utilities ────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Token Utilities ───────────────────────────────────────

def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "sub": subject,
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow(),
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a JWT refresh token with longer expiry."""
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
        "iat": datetime.utcnow(),
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI Dependencies ─────────────────────────────────────

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    FastAPI dependency to extract and validate the current user from JWT.

    Use as: `current_user: dict = Depends(get_current_user)`
    Returns: {"sub": "user_id", "exp": ..., "type": "access"}
    """
    token = credentials.credentials
    payload = decode_token(token)

    # Ensure it's an access token (not a refresh token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def get_optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict | None:
    """
    Optional authentication — returns user if valid token, None otherwise.
    Use for endpoints that work for both authenticated and anonymous users.
    """
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") == "access":
            return payload
    except HTTPException:
        pass

    return None


def create_tokens_for_user(user_id: str) -> Token:
    """Create both access and refresh tokens for a user."""
    return Token(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


def get_current_user_from_refresh(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Validate a REFRESH token specifically for /auth/refresh."""
    token = credentials.credentials
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: expected refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
