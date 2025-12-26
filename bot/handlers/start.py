"""
Start command handler
"""
from telegram import Update
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command
    """
    message = """
🤖 **Analisa Saham AI Bot**

Selamat datang! Bot ini membantu Anda menganalisis saham Indonesia menggunakan AI.

**Cara menggunakan:**
`/analisa TICKER`

Contoh:
`/analisa BBCA`
`/analisa ASII`
`/analisa MDLA`

**Fitur:**
• Analisis teknikal lengkap
• Chart harga dengan EMA
• Laporan AI profesional
• Sistem kuota per user

Mulai analisis saham Anda sekarang! 🚀
"""
    
    await update.message.reply_text(
        message,
        parse_mode='Markdown'
    )
