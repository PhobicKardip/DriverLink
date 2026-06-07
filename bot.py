import re
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = "8849663961:AAHDnl2ooXZGBovLkFEn7NPc_XdkX_F6QQ4"
PESAN = "Hallo ka, aku dari driver Maxim"

logging.basicConfig(level=logging.INFO)

def konversi_nomor(teks):
    nomor = re.sub(r'[\s\-\(\)\+]', '', teks)
    nomor = re.sub(r'\D', '', nomor)
    
    if nomor.startswith('62'):
        pass
    elif nomor.startswith('0'):
        nomor = '62' + nomor[1:]
    else:
        return None
    
    if len(nomor) < 10 or len(nomor) > 15:
        return None
    
    return nomor

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = update.message.text.strip()
    nomor = konversi_nomor(teks)
    
    if nomor:
        link = f"https://wa.me/{nomor}?text={PESAN.replace(' ', '%20')}"
        await update.message.reply_text(link)
    else:
        await update.message.reply_text("Format nomor tidak dikenal. Coba kirim:\n085xxxxxxx\n+62 85xxxxxxx\n6285xxxxxxx")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hallo! Kirim nomor HP pelanggan, aku langsung buatin link WA-nya.")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot jalan...")
app.run_polling()
