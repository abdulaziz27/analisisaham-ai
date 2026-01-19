"""
Quota Router
Handles quota checking and management endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.models.database import get_db
from backend.app.services.quota import check_quota, decrement_quota, get_quota_info

router = APIRouter()


class QuotaCheckResponse(BaseModel):
    ok: bool
    remaining: int


class QuotaDecrementRequest(BaseModel):
    user_id: str


@router.get(
    "/check", 
    response_model=QuotaCheckResponse,
    summary="Cek Kuota Pengguna",
    description="Mengecek sisa kuota analisis untuk user ID tertentu."
)
async def check_user_quota(
    user_id: str = Query(..., description="ID Telegram User untuk dicek kuotanya", example="12345678"),
    username: str = Query(None, description="Username Telegram"),
    first_name: str = Query(None, description="Nama Depan"),
    last_name: str = Query(None, description="Nama Belakang"),
    language_code: str = Query(None, description="Bahasa"),
    is_premium: bool = Query(None, description="Status Premium"),
    db: Session = Depends(get_db)
):
    """
    Check user's remaining quota and update profile info
    """
    try:
        quota_info = await get_quota_info(
            user_id, 
            db=db,
            username=username, 
            first_name=first_name, 
            last_name=last_name, 
            language_code=language_code, 
            is_premium=is_premium
        )
        
        if quota_info is None:
            # User doesn't exist, create with 3 free requests
            return QuotaCheckResponse(ok=True, remaining=3)
        
        remaining = quota_info.get("remaining", 0)
        return QuotaCheckResponse(
            ok=remaining > 0,
            remaining=remaining
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking quota: {str(e)}"
        )


@router.post(
    "/decrement",
    summary="Kurangi Kuota Pengguna",
    description="Mengurangi kuota pengguna sebanyak 1 unit. Mengembalikan error 400 jika kuota habis."
)
async def decrement_user_quota(
    request: QuotaDecrementRequest,
    db: Session = Depends(get_db)
):
    """
    Decrement user's quota. Atomic operation.
    """
    try:
        success = await decrement_quota(request.user_id, db=db)
        
        if success:
            return {"ok": True, "message": "Quota decremented"}
        else:
            # Return 200 OK but with ok=False to let client handle logic gracefully
            return {"ok": False, "message": "Quota habis"}
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error decrementing quota: {str(e)}"
        )
