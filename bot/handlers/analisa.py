"""
Analisa command handler
Handles /analisa TICKER command
"""
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.core.http_client import get_http_client, BASE_URL


async def analisa_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /analisa TICKER command
    
    Flow:
    1. Check quota
    2. If no quota → show upgrade button
    3. If quota available → decrement, process, send results
    """
    user_id = str(update.effective_user.id)
    user_data = {
        "user_id": user_id,
        "username": update.effective_user.username,
        "first_name": update.effective_user.first_name,
        "last_name": update.effective_user.last_name,
        "language_code": update.effective_user.language_code,
        "is_premium": getattr(update.effective_user, 'is_premium', False)
    }
    
    # Parse ticker from command
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Format: /analisa TICKER\nContoh: /analisa BBCA"
        )
        return
    
    ticker = context.args[0].upper().strip()
    
    try:
        client = get_http_client()
        
        # Step 1: Check quota (and update user info)
        quota_response = await client.get(
            f"{BASE_URL}/quota/check",
            params=user_data
        )
        
        if quota_response.status_code != 200:
            await update.message.reply_text(
                "⚠️ Server sibuk, coba lagi nanti."
            )
            return
        
        quota_data = quota_response.json()
        
        if not quota_data.get("ok") or quota_data.get("remaining", 0) <= 0:
            # No quota - show upgrade button
            keyboard = [
                [InlineKeyboardButton("🔝 Upgrade Plan", callback_data="upgrade")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ Kuota habis. Silakan upgrade plan Anda untuk melanjutkan.",
                reply_markup=reply_markup
            )
            return
        
        # Step 2: Send processing message
        processing_msg = await update.message.reply_text(
            f"⏳ Sedang menganalisis {ticker}...\nMohon tunggu sebentar."
        )
        
        # Step 3: Early decrement quota
        await client.post(
            f"{BASE_URL}/quota/decrement",
            json={"user_id": user_id}
        )
        
        # Step 4: Call analyze endpoint
        analyze_response = await client.post(
            f"{BASE_URL}/api/analyze",
            json={"ticker": ticker, "user_id": user_id}
        )
        
        if analyze_response.status_code != 200:
            error_detail = analyze_response.json().get("detail", "Unknown error")
            await processing_msg.edit_text(
                f"❌ Error: {error_detail[:200]}"
            )
            return
        
        data = analyze_response.json()
        
        # Step 5: Format and send results
        indicators = data.get("indicators", {})
        ai_report = data.get("ai_report", "")
        
        # Format summary message
        price = indicators.get("current_price", 0)
        change_pct = indicators.get("price_change_percent", 0)
        change_7d = indicators.get("price_change_7d")
        change_30d = indicators.get("price_change_30d")
        rsi = indicators.get("rsi", 0)
        support = indicators.get("support", 0)
        resistance = indicators.get("resistance", 0)
        ema20 = indicators.get("ema20", 0)
        ema50 = indicators.get("ema50", 0)
        volume_avg = indicators.get("volume_avg", 0)
        
        # Determine trend
        trend_icon = "📈" if change_pct > 0 else "📉" if change_pct < 0 else "➡️"
        trend_text = "Naik" if change_pct > 0 else "Turun" if change_pct < 0 else "Sideways"
        
        # RSI context
        rsi_status = ""
        if rsi > 70:
            rsi_status = " 🔴 (Overbought)"
        elif rsi < 30:
            rsi_status = " 🟢 (Oversold)"
        elif rsi > 60:
            rsi_status = " ⚠️ (Mendekati Overbought)"
        elif rsi < 40:
            rsi_status = " ⚠️ (Mendekati Oversold)"
        
        # EMA relation
        if ema20 and ema50:
            ema_relation = "EMA20 > EMA50 (Bullish)" if ema20 > ema50 else "EMA20 < EMA50 (Bearish)"
        else:
            ema_relation = "N/A"
        
        # MACD summary
        macd = indicators.get("macd", 0)
        macd_signal = "Positif" if macd and macd > 0 else "Negatif"
        
        # Calculate entry ideal range (between support and EMA20/50, whichever is closer to current price)
        entry_low = support
        entry_high = min(ema20 if ema20 else price, resistance * 0.98)  # 2% below resistance
        if entry_high <= entry_low:
            entry_high = price * 1.02  # 2% above current if calculation fails
        
        # Period change info
        period_info = f"1 hari: {change_pct:+.2f}%"
        if change_7d is not None:
            period_info += f" | 7 hari: {change_7d:+.2f}%"
        if change_30d is not None:
            period_info += f" | 30 hari: {change_30d:+.2f}%"
        
        # Sanitize AI Report for Telegram Legacy Markdown
        # 1. Replace ** with * (Gemini bold -> Telegram bold)
        ai_report = ai_report.replace("**", "*")
        # 2. Replace * at start of lines with • (Gemini bullet -> Safe bullet)
        ai_report = ai_report.replace("* ", "• ")
        ai_report = ai_report.replace("\n*", "\n•")
        # 3. Remove underscores to prevent broken italics (e.g. in Stop_Loss)
        ai_report = ai_report.replace("_", " ")
        
        summary = f"""🤖 *ANALISA SAHAM — {ticker}*

📊 *Harga Terakhir:* Rp {price:,.0f}
{trend_icon} *Perubahan:* {period_info}

*1) Level Penting*
• Support: Rp {support:,.0f}
• Resistance: Rp {resistance:,.0f}
• Entry Ideal: Rp {entry_low:,.0f} - Rp {entry_high:,.0f}
• EMA20: Rp {ema20:,.0f} | EMA50: Rp {ema50:,.0f}

*2) Momentum*
• RSI: {rsi:.2f}{rsi_status}
• {ema_relation}
• MACD: {macd_signal}

*3) Analisis AI*
{ai_report}

📎 Chart terlampir.
🔧 Gunakan tombol di bawah untuk aksi lainnya."""
        
        # Delete processing message
        await processing_msg.delete()
        
        # Send summary
        keyboard = [
            [
                InlineKeyboardButton("Save Watchlist", callback_data=f"save:{ticker}")
            ],
            [InlineKeyboardButton("Upgrade Plan", callback_data="upgrade")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            summary,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Step 6: Send chart if available
        chart_path = data.get("chart_path")
        if chart_path and os.path.exists(chart_path):
            try:
                with open(chart_path, 'rb') as chart_file:
                    await update.message.reply_photo(
                        photo=chart_file,
                        caption=f"📊 Chart Teknikal {ticker}"
                    )
                # Clean up chart file
                os.remove(chart_path)
            except Exception as e:
                # Just log error, don't spam user
                print(f"Error sending chart: {e}")
    
    except Exception as e:
        error_msg = str(e)
        
        # Handle specific errors
        if "sedang sibuk" in error_msg.lower() or "overloaded" in error_msg.lower() or "503" in error_msg:
            await update.message.reply_text(
                "⚠️ Model AI sedang sibuk saat ini.\n\n"
                "Silakan coba lagi dalam beberapa detik.\n"
                "Kami sedang memproses banyak request."
            )
        elif "kuota" in error_msg.lower():
            keyboard = [[InlineKeyboardButton("🔝 Upgrade Plan", callback_data="upgrade")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Kuota habis. Silakan upgrade plan Anda.",
                reply_markup=reply_markup
            )
        else:
            # Generic error
            await update.message.reply_text(
                f"Error: {error_msg[:300]}"
            )
