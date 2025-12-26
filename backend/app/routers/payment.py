
"""
Payment Router
Handles payment creation and webhooks
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.app.services.payment import create_transaction, process_notification
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class CreateTransactionRequest(BaseModel):
    user_id: str
    plan_id: str

@router.post("/create", summary="Create Payment Link")
async def create_payment(request: CreateTransactionRequest):
    """
    Create a Midtrans payment link for a specific plan
    """
    try:
        result = await create_transaction(request.user_id, request.plan_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notification", summary="Midtrans Webhook")
async def midtrans_notification(request: Request):
    """
    Handle Midtrans payment notification
    """
    try:
        notification_data = await request.json()
        result = await process_notification(notification_data)
        return result
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        # Always return 200 to Midtrans even if error, to stop retries (unless we want retries)
        # But for debugging it's better to raise
        return {"status": "error", "message": str(e)}
