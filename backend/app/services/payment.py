"""
Payment Service
Handles Midtrans integration and transaction management using SQLAlchemy ORM
"""
import midtransclient
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.models.database import PaymentTransaction, UserQuota
from backend.app.core.http_client import get_http_client
import logging
import json
import time
import uuid
from typing import Optional
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

# Initialize Midtrans Core API
core_api = midtransclient.CoreApi(
    is_production=settings.MIDTRANS_IS_PRODUCTION,
    server_key=settings.MIDTRANS_SERVER_KEY,
    client_key=settings.MIDTRANS_CLIENT_KEY
)

# Define Plans
PLANS = {
    "basic": {"name": "Paket Basic", "price": 50000, "quota": 30},
    "pro": {"name": "Paket Pro", "price": 100000, "quota": 100},
    "sultan": {"name": "Paket Sultan", "price": 500000, "quota": 1000},
}


async def create_transaction(
    user_id: str, 
    plan_id: str,
    db: Session
) -> dict:
    """
    Create a new QRIS transaction via Core API
    
    Args:
        user_id: Telegram user ID
        plan_id: Plan identifier (basic, pro, sultan)
        db: Database session
    
    Returns:
        Dict with transaction details including payment URL
    """
    if plan_id not in PLANS:
        raise ValueError(f"Invalid plan_id: {plan_id}")
    
    plan = PLANS[plan_id]
    order_id = f"ORDER-{user_id}-{int(time.time())}-{str(uuid.uuid4())[:4]}"
    
    # Calculate custom expiry (15 minutes)
    expiry_duration = 15
    
    param = {
        "payment_type": "qris",
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": plan["price"]
        },
        "custom_expiry": {
            "expiry_duration": expiry_duration,
            "unit": "minute"
        },
        "customer_details": {
            "user_id": user_id,
        },
        "item_details": [{
            "id": plan_id,
            "price": plan["price"],
            "quantity": 1,
            "name": plan["name"]
        }],
        "qris": {
            "acquirer": "gopay"
        }
    }
    
    try:
        # Create Core API Transaction
        response = core_api.charge(param)
        
        # Calculate expiry time string for display
        tz_wib = pytz.timezone('Asia/Jakarta')
        now = datetime.now(tz_wib)
        expiry_time = now + timedelta(minutes=expiry_duration)
        expiry_str = expiry_time.strftime("%H:%M WIB")
        
        # Extract QR Code URL
        qr_url = None
        if 'actions' in response:
            for action in response['actions']:
                if action['name'] == 'generate-qr-code':
                    qr_url = action['url']
                    break
        
        # Save to DB using ORM
        transaction = PaymentTransaction(
            order_id=order_id,
            user_id=user_id,
            plan_id=plan_id,
            amount=plan["price"],
            status="pending",
            payment_type="qris",
            midtrans_response=json.dumps(response)
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        logger.info(f"Created transaction {order_id} for user {user_id}, plan {plan_id}")
        
        return {
            "order_id": order_id,
            "payment_url": qr_url,
            "plan_name": plan["name"],
            "amount": plan["price"],
            "type": "qris",
            "expiry_time": expiry_str
        }
        
    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        db.rollback()
        raise Exception(f"Gagal membuat QRIS: {str(e)}")


async def send_telegram_notification(user_id: str, message: str):
    """Send notification to user via Telegram API"""
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        client = get_http_client()
        await client.post(url, json={
            "chat_id": user_id,
            "text": message,
            "parse_mode": "Markdown"
        })
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")


async def process_notification(
    notification_data: dict,
    db: Session
) -> dict:
    """
    Process Midtrans notification webhook
    
    Args:
        notification_data: Midtrans notification payload
        db: Database session
    
    Returns:
        Dict with processing status
    """
    try:
        # Extract variables
        order_id = notification_data.get('order_id')
        transaction_status = notification_data.get('transaction_status')
        fraud_status = notification_data.get('fraud_status')
        
        logger.info(f"Processing notification for order {order_id}: {transaction_status}")
        
        # Determine new status
        new_status = 'pending'
        if transaction_status == 'capture':
            if fraud_status == 'challenge':
                new_status = 'challenge'
            else:
                new_status = 'success'
        elif transaction_status == 'settlement':
            new_status = 'success'
        elif transaction_status in ['cancel', 'deny', 'expire']:
            new_status = 'failed'
        elif transaction_status == 'pending':
            new_status = 'pending'
        
        # Get transaction from DB
        transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.order_id == order_id
        ).first()
        
        if not transaction:
            logger.warning(f"Transaction {order_id} not found")
            return {"status": "not_found"}
        
        # Skip if already success (idempotent)
        if transaction.status == 'success':
            logger.info(f"Transaction {order_id} already success, ignoring")
            return {"status": "ok", "message": "Already success"}
        
        # Update transaction status
        transaction.status = new_status
        transaction.midtrans_response = json.dumps(notification_data)
        if 'transaction_time' in notification_data:
            try:
                transaction.transaction_time = datetime.fromisoformat(
                    notification_data['transaction_time'].replace('Z', '+00:00')
                )
            except:
                pass
        if 'settlement_time' in notification_data:
            try:
                transaction.settlement_time = datetime.fromisoformat(
                    notification_data['settlement_time'].replace('Z', '+00:00')
                )
            except:
                pass
        
        db.commit()
        
        # If success, add quota AND notify user
        if new_status == 'success':
            quota_to_add = PLANS[transaction.plan_id]["quota"]
            plan_name = PLANS[transaction.plan_id]["name"]
            
            logger.info(f"Adding {quota_to_add} quota to user {transaction.user_id}")
            
            # Update user quota
            quota = db.query(UserQuota).filter(
                UserQuota.user_id == transaction.user_id
            ).first()
            
            if quota:
                quota.requests_remaining += quota_to_add
            else:
                # Create quota if doesn't exist
                quota = UserQuota(
                    user_id=transaction.user_id,
                    requests_remaining=quota_to_add,
                    total_requests=0
                )
                db.add(quota)
            
            db.commit()
            db.refresh(quota)
            
            # Send notification
            await send_telegram_notification(
                transaction.user_id,
                f"✅ *Pembayaran Berhasil!*\n\n"
                f"📦 Paket: {plan_name}\n"
                f"➕ Kuota Ditambah: +{quota_to_add}\n"
                f"🎫 *Total Kuota Sekarang: {quota.requests_remaining}*\n\n"
                f"Selamat menganalisis! 🚀"
            )
        
        # If failed, notify user
        elif new_status == 'failed':
            plan_name = PLANS[transaction.plan_id]["name"]
            logger.info(f"Transaction {order_id} failed for user {transaction.user_id}")
            
            await send_telegram_notification(
                transaction.user_id,
                f"❌ *Pembayaran Gagal/Kadaluarsa*\n\n"
                f"📦 Paket: {plan_name}\n"
                f"Status: {transaction_status.capitalize()}\n\n"
                f"Silakan lakukan pemesanan ulang jika masih berminat."
            )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing notification: {str(e)}")
        db.rollback()
        raise Exception(f"Notification processing error: {str(e)}")
