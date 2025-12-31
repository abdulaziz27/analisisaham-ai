
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
    Create a new QRIS transaction via Core API
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
        
        # Calculate expiry time string for display (approximate based on request time)
        # Midtrans response usually has transaction_time, but expiry_time depends on custom_expiry
        # We'll calculate it locally for display accuracy
        from datetime import datetime, timedelta
        import pytz
        
        # WIB Timezone
        tz_wib = pytz.timezone('Asia/Jakarta')
        now = datetime.now(tz_wib)
        expiry_time = now + timedelta(minutes=expiry_duration)
        expiry_str = expiry_time.strftime("%H:%M WIB")
        
        # Extract QR Code URL
        # For Sandbox, actions might contain the qr url
        qr_url = None
        if 'actions' in response:
            for action in response['actions']:
                if action['name'] == 'generate-qr-code':
                    qr_url = action['url']
                    break
        
        # Fallback/Direct access (depends on Midtrans version response)
        if not qr_url and 'qr_string' in response:
             # If raw QR string is provided, we might need to generate image ourselves
             # But usually actions['url'] is the image for Sandbox
             pass
             
        # In Sandbox, QRIS is simulated via GoPay
        if settings.MIDTRANS_IS_PRODUCTION is False and not qr_url:
             # Sandbox often returns actions for simulator
             pass

        # Save to DB
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO transactions (order_id, user_id, plan_id, amount, status, payment_url, snap_token)
                VALUES (:order_id, :user_id, :plan_id, :amount, 'pending', :payment_url, NULL)
            """), {
                "order_id": order_id,
                "user_id": user_id,
                "plan_id": plan_id,
                "amount": plan["price"],
                "payment_url": qr_url, # Store QR Image URL here
            })
            conn.commit()
            
        return {
            "order_id": order_id,
            "payment_url": qr_url, # This will be the QR Image URL
            "plan_name": plan["name"],
            "amount": plan["price"],
            "type": "qris",
            "expiry_time": expiry_str
        }
        
    except Exception as e:
        logger.error(f"Error creating transaction: {str(e)}")
        raise Exception(f"Gagal membuat QRIS: {str(e)}")

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
                
                # Update and get new total
                result = conn.execute(text("""
                    UPDATE user_quotas 
                    SET 
                        requests_remaining = requests_remaining + :quota,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id
                    RETURNING requests_remaining
                """), {"quota": quota_to_add, "user_id": user_id})
                
                new_total = result.scalar()
                conn.commit()
                
                # SEND NOTIFICATION
                await send_telegram_notification(
                    user_id, 
                    f"✅ *Pembayaran Berhasil!*\n\n"
                    f"📦 Paket: {plan_name}\n"
                    f"➕ Kuota Ditambah: +{quota_to_add}\n"
                    f"🎫 *Total Kuota Sekarang: {new_total}*\n\n"
                    f"Selamat menganalisis! 🚀"
                )
            
            # If failed, notify user
            elif new_status == 'failed':
                plan_name = PLANS[plan_id]["name"]
                logger.info(f"Transaction {order_id} failed for user {user_id}")
                
                await send_telegram_notification(
                    user_id,
                    f"❌ *Pembayaran Gagal/Kadaluarsa*\n\n"
                    f"📦 Paket: {plan_name}\n"
                    f"Status: {transaction_status.capitalize()}\n\n"
                    f"Silakan lakukan pemesanan ulang jika masih berminat."
                )
                
        return {"status": "ok"}

        
    except Exception as e:
        logger.error(f"Error processing notification: {str(e)}")
        raise Exception(f"Notification processing error: {str(e)}")
