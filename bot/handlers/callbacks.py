"""
Callback query handlers
Handles inline button callbacks
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.core.http_client import get_http_client, BASE_URL


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
            client = get_http_client()
            response = await client.post(
                f"{BASE_URL}/payment/create",
                json={"user_id": user_id, "plan_id": plan_id}
            )
            
            if response.status_code == 200:
                result = response.json()
                qr_url = result.get("payment_url")
                plan_name = result.get("plan_name")
                amount = result.get("amount")
                expiry_time = result.get("expiry_time", "15 Menit")
                
                if qr_url:
                    # Send QR Code Image
                    await query.delete_message()
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=qr_url,
                        caption=(
                            f"🧾 *Scan QRIS*\n\n"
                            f"📦 Paket: {plan_name}\n"
                            f"💰 Total: Rp {amount:,.0f}\n"
                            f"⏳ *Berlaku s/d: {expiry_time}*\n\n"
                            "1. Buka Gojek/OVO/Shopee/BCA Mobile\n"
                            "2. Scan QR di atas\n"
                            "3. Kuota masuk otomatis setelah bayar!\n\n"
                            f"🔗 [Link QRIS untuk Simulator]({qr_url})"
                        ),
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text("❌ Gagal generate QRIS. Coba lagi nanti.")
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
