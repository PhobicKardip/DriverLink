import re
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8849663961:AAHDnl2ooXZGBovLkFEn7NPc_XdkX_F6QQ4"
PESAN = "Hallo, aku dari Maxim"

TUNGGU_TARIF = 1

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

def hitung_tarif(tarif):
    komisi = tarif * 0.13
    sisa = tarif - komisi
    bensin = sisa * 0.10
    saldo = sisa * 0.10
    kantong = sisa * 0.80

    return f"""
💰 Tarif Masuk: Rp {tarif:,.0f}
✂️ Potongan Apk (13%): -Rp {komisi:,.0f}
Sisa Bersih Aplikasi: Rp {sisa:,.0f}

📥 Alokasi Dicicil (Masing-masing 10%):
⛽ Bensin: Rp {bensin:,.0f}
💳 Saldo: Rp {saldo:,.0f}

🏁 UANG BERSIH KANTONG (80%): Rp {kantong:,.0f}
"""

async def handle_nomor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = update.message.text.strip()
    nomor = konversi_nomor(teks)
    
    if nomor:
        link = f"https://wa.me/{nomor}?text={PESAN.replace(' ', '%20')}"
        await update.message.reply_text(link)
        await update.message.reply_text("Tarif berapa? (contoh: 15000)")
        return TUNGGU_TARIF
    else:
        await update.message.reply_text("Format nomor tidak dikenal. Coba kirim:\n085xxxxxxx\n+62 85xxxxxxx\n6285xxxxxxx")
        return ConversationHandler.END

async def handle_tarif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = re.sub(r'\D', '', update.message.text.strip())
    
    if teks:
        tarif = int(teks)
        hasil = hitung_tarif(tarif)
        await update.message.reply_text(hasil)
    else:
        await update.message.reply_text("Angka tidak valid, coba lagi.")
    
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hallo! Kirim nomor HP pelanggan, aku langsung buatin link WA dan hitung alokasi tarif kamu.")

app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_nomor)],
    states={
        TUNGGU_TARIF: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tarif)],
    },
    fallbacks=[CommandHandler("start", start)],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)

print("Bot jalan...")
app.run_polling()
