"""
Quota check command handler
Handles /kuota or /info command
"""
import httpx
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

async def kuota_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Check user's remaining quota
    """
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BASE_URL}/quota/check",
                params={"user_id": user_id}
            )
            
            if response.status_code == 200:
                data = response.json()
                remaining = data.get("remaining", 0)
                
                # Create message
                msg = (
                    f"👤 **Info Akun: {user_name}**\n\n"
                    f"🎫 **Sisa Kuota:** {remaining} request\n"
                    f"🆔 **ID:** `{user_id}`\n\n"
                )
                
                if remaining < 5:
                    msg += "⚠️ Kuota menipis! Segera isi ulang."
                    
                # Add Topup Button
                keyboard = [
                    [InlineKeyboardButton("🔝 Isi Ulang Kuota", callback_data="upgrade")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ Gagal mengecek kuota. Server sibuk.")
                
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
