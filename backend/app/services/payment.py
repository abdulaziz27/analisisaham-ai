
"""
Payment Service
Handles Midtrans integration and transaction management
"""
import midtransclient
from sqlalchemy import text
from backend.app.core.config import settings
from backend.app.services.quota import engine
import logging
import json
import time
import uuid

logger = logging.getLogger(__name__)

# Initialize Midtrans Snap API
snap = midtransclient.Snap(
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

def ensure_payment_tables():
    """Create transactions table if not exists"""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS transactions (
                    order_id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    plan_id VARCHAR(50) NOT NULL,
                    amount INTEGER NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    payment_url TEXT,
                    snap_token VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.commit()
    except Exception as e:
        logger.error(f"Error creating payment tables: {str(e)}")

# Initialize tables on module load
ensure_payment_tables()

async def create_transaction(user_id: str, plan_id: str) -> dict:
    """
    Create a new transaction and get Midtrans payment URL
    """
    if plan_id not in PLANS:
        raise ValueError(f"Invalid plan_id: {plan_id}")
    
    plan = PLANS[plan_id]
    order_id = f"ORDER-{user_id}-{int(time.time())}-{str(uuid.uuid4())[:4]}"
    
    param = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": plan["price"]
        },
        "customer_details": {
            "user_id": user_id,
        },
        "item_details": [{
            "id": plan_id,
            "price": plan["price"],
            "quantity": 1,
            "name": plan["name"]
        }]
    }
    
    try:
        # Create Snap Token
        transaction = snap.create_transaction(param)
        payment_url = transaction['redirect_url']
        token = transaction['token']
        
        # Save to DB
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO transactions (order_id, user_id, plan_id, amount, status, payment_url, snap_token)
                VALUES (:order_id, :user_id, :plan_id, :amount, 'pending', :payment_url, :token)
            """), {
                "order_id": order_id,
                "user_id": user_id,
                "plan_id": plan_id,
                "amount": plan["price"],
                "payment_url": payment_url,
                "token": token
            })
            conn.commit()
            
        return {
            "order_id": order_id,
            "payment_url": payment_url,
            "plan_name": plan["name"],
            "amount": plan["price"]
        }
        
    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        raise Exception("Gagal membuat transaksi pembayaran")

import httpx

# ... (imports existing)

async def send_telegram_notification(user_id: str, message: str):
    """Send notification to user via Telegram API"""
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={
                "chat_id": user_id,
                "text": message,
                "parse_mode": "Markdown"
            })
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")

async def process_notification(notification_data: dict) -> dict:
    """
    Process Midtrans notification webhook
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
        elif transaction_status == 'cancel' or transaction_status == 'deny' or transaction_status == 'expire':
            new_status = 'failed'
        elif transaction_status == 'pending':
            new_status = 'pending'
        
        # Update Transaction Status
        with engine.connect() as conn:
            # Check current status first
            result = conn.execute(text("SELECT status, user_id, plan_id FROM transactions WHERE order_id = :order_id"), {"order_id": order_id})
            row = result.fetchone()
            
            if not row:
                logger.warning(f"Transaction {order_id} not found")
                return {"status": "not_found"}
                
            current_status, user_id, plan_id = row
            
            if current_status == 'success':
                logger.info(f"Transaction {order_id} already success, ignoring")
                return {"status": "ok", "message": "Already success"}
            
            # Update status
            conn.execute(text("""
                UPDATE transactions 
                SET status = :status, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = :order_id
            """), {"status": new_status, "order_id": order_id})
            conn.commit()
            
            # If success, add quota AND notify user
            if new_status == 'success':
                quota_to_add = PLANS[plan_id]["quota"]
                plan_name = PLANS[plan_id]["name"]
                
                logger.info(f"Adding {quota_to_add} quota to user {user_id}")
                
                conn.execute(text("""
                    UPDATE user_quotas 
                    SET 
                        requests_remaining = requests_remaining + :quota,
                        total_requests = total_requests,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id
                """), {"quota": quota_to_add, "user_id": user_id})
                conn.commit()
                
                # SEND NOTIFICATION
                await send_telegram_notification(
                    user_id, 
                    f"✅ **Pembayaran Berhasil!**\n\n"
                    f"Paket: {plan_name}\n"
                    f"Kuota Ditambah: +{quota_to_add}\n\n"
                    f"Selamat menganalisis! 🚀"
                )
                
        return {"status": "ok"}

        
    except Exception as e:
        logger.error(f"Error processing notification: {str(e)}")
        raise Exception(f"Notification processing error: {str(e)}")
