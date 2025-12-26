"""
Callback query handlers
Handles inline button callbacks
"""
import os
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle callback queries from inline buttons
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(update.effective_user.id)
    
    if data == "upgrade":
        # Upgrade plan menu
        keyboard = [
            [InlineKeyboardButton("💰 Basic (Rp 50rb / 30 req)", callback_data="buy:basic")],
            [InlineKeyboardButton("💎 Pro (Rp 100rb / 100 req)", callback_data="buy:pro")],
            [InlineKeyboardButton("👑 Sultan (Rp 500rb / 1000 req)", callback_data="buy:sultan")],
            [InlineKeyboardButton("🔙 Batal", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔝 **Upgrade Plan**\n\n"
            "Silakan pilih paket kuota tambahan:\n"
            "Kuota berlaku selamanya (tidak hangus).",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    elif data.startswith("buy:"):
        plan_id = data.replace("buy:", "")
        
        # Show loading state
        await query.edit_message_text("⏳ Sedang membuat link pembayaran...")
        
        try:
            # Call backend to create payment
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{BASE_URL}/payment/create",
                    json={"user_id": user_id, "plan_id": plan_id}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    payment_url = result.get("payment_url")
                    plan_name = result.get("plan_name")
                    amount = result.get("amount")
                    
                    keyboard = [
                        [InlineKeyboardButton("💳 Bayar Sekarang", url=payment_url)]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"🧾 **Tagihan Pembayaran**\n\n"
                        f"Item: {plan_name}\n"
                        f"Harga: Rp {amount:,.0f}\n\n"
                        "Klik tombol di bawah untuk melanjutkan pembayaran via Midtrans (QRIS, GoPay, VA Bank).",
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                else:
                    error_msg = response.json().get("detail", "Unknown error")
                    await query.edit_message_text(f"❌ Gagal membuat tagihan: {error_msg}")
                    
        except Exception as e:
            await query.edit_message_text(f"❌ Error koneksi: {str(e)}")

    elif data == "cancel":
        await query.delete_message()
    
    elif data.startswith("save:"):
        # Save to watchlist
        ticker = data.replace("save:", "")
        await query.edit_message_text(
            f"💾 **{ticker}** telah disimpan ke watchlist Anda.\n\n"
            "Fitur watchlist sedang dalam pengembangan! 📝",
            parse_mode='Markdown'
        )
