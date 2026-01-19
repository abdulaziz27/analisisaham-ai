"""
Payment Router
Handles payment creation and webhooks
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.models.database import get_db
from backend.app.services.payment import create_transaction, process_notification
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class CreateTransactionRequest(BaseModel):
    user_id: str
    plan_id: str


@router.post("/create", summary="Create Payment Link")
async def create_payment(
    request: CreateTransactionRequest,
    db: Session = Depends(get_db)
):
    """
    Create a Midtrans payment link for a specific plan
    """
    try:
        result = await create_transaction(request.user_id, request.plan_id, db=db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notification", summary="Midtrans Webhook")
async def midtrans_notification(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Midtrans payment notification
    """
    try:
        notification_data = await request.json()
        result = await process_notification(notification_data, db=db)
        return result
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        # Always return 200 to Midtrans even if error, to stop retries
        return {"status": "error", "message": str(e)}
