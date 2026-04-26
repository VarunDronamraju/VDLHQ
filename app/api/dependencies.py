import os
import uuid
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

JWT_SECRET = os.getenv("JWT_SECRET", "supersecret-locationhq-2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


class AuthenticatedUser(BaseModel):
    user_id: str
    role: str
    client_id: Optional[uuid.UUID] = None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> AuthenticatedUser:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        client_id_str: Optional[str] = payload.get("client_id")

        if user_id is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        client_id = None
        if client_id_str:
            try:
                client_id = uuid.UUID(client_id_str)
            except ValueError:
                pass

        return AuthenticatedUser(user_id=user_id, role=role, client_id=client_id)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_ops(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if user.role != "ops":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted to ops role",
        )
    return user
