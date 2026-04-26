import jwt
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.api.dependencies import JWT_SECRET, JWT_ALGORITHM

router = APIRouter()

class RoleLoginRequest(BaseModel):
    role: str

@router.post("/login")
async def login(request: RoleLoginRequest):
    # SIMPLIFIED ROLE-BASED LOGIN FOR MVP DEMO
    if request.role not in ["client", "ops"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'client' or 'ops'."
        )

    # Fixed user IDs for demo
    user_id = "ops-demo-1" if request.role == "ops" else "client-demo-1"
    
    # Fixed client ID for client dashboard demo (matching system data if possible)
    # Note: In a real system, this would be looked up.
    # For now, we use a consistent ID that should have data in the system.
    client_id = "00000000-0000-0000-0000-000000000001" if request.role == "client" else None

    payload = {
        "sub": user_id,
        "role": request.role,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    
    if client_id:
        payload["client_id"] = client_id

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}
