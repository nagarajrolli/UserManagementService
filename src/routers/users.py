from fastapi import APIRouter, Depends, status, HTTPException
from src.schemas.user_schemas import UserCreate, UserResponse
from src.dependencies.auth import verify_api_key_header

# Instantiate the localized mini-router
router = APIRouter()

# Temporary in-memory state representation
MOCK_USER_DB = {}


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(payload: UserCreate):
    """
    Public Endpoint: Anyone can request to register a user.
    Uses schemas to handle request validation and parse the response output securely.
    """
    if payload.email in MOCK_USER_DB:
        raise HTTPException(status_code=400, detail="Email already registered.")

    user_id = len(MOCK_USER_DB) + 1
    new_user = {
        "id": user_id,
        "email": payload.email,
        "username": payload.username,
        "is_active": True
    }
    MOCK_USER_DB[payload.email] = new_user
    return new_user


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(token: str = Depends(verify_api_key_header)):
    """
    Protected Endpoint: Inherits secure localized dependency validation.
    """
    # Simply returns mock data if dependency successfully resolves
    return {"id": 99, "email": "admin@domain.com", "username": "admin_user", "is_active": True}
