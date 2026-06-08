import re
import logging
from datetime import time
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8849663961:AAHDnl2ooXZGBovLkFEn7NPc_XdkX_F6QQ4"
PESAN = "Hallo, aku dari Maxim"
CHAT_ID = 8036036520

TUNGGU_TARIF = 1

logging.basicConfig(level=logging.INFO)

data_hari = {
    "orders": [],
    "total_kotor": 0,
    "total_potongan": 0,
    "total_bersih": 0,
    "total_bensin": 0,
    "total_saldo": 0,
    "total_kantong": 0,
}

def reset_data():
    for key in data_hari:
        data_hari[key] = [] if key == "orders" else 0

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

def is_nomor_hp(teks):
    nomor = re.sub(r'[\s\-\(\)\+]', '', teks)
    nomor = re.sub(r'\D', '', nomor)
    return (nomor.startswith('62') or nomor.startswith('0')) and 10 <= len(nomor) <= 15

def hitung_tarif(tarif):
    komisi = tarif * 0.13
    sisa = tarif - komisi
    bensin = sisa * 0.10
    saldo = sisa * 0.10
    kantong = sisa * 0.80

    data_hari["orders"].append(tarif)
    data_hari["total_kotor"] += tarif
    data_hari["total_potongan"] += komisi
    data_hari["total_bersih"] += sisa
    data_hari["total_bensin"] += bensin
    data_hari["total_saldo"] += saldo
    data_hari["total_kantong"] += kantong

    n = len(data_hari["orders"])

    return f"""
💰 Tarif Masuk: Rp {tarif:,.0f}
✂️ Potongan Apk (13%): -Rp {komisi:,.0f}
Sisa Bersih Aplikasi: Rp {sisa:,.0f}

📥 Alokasi Dicicil (Masing-masing 10%):
⛽ Bensin: Rp {bensin:,.0f}
💳 Saldo: Rp {saldo:,.0f}

🏁 UANG BERSIH KANTONG (80%): Rp {kantong:,.0f}

━━━━━━━━━━━━━━━━
📊 Rekap Hari Ini ({n} order):
💵 Total Kotor: Rp {data_hari['total_kotor']:,.0f}
✂️ Total Potongan: Rp {data_hari['total_potongan']:,.0f}
✅ Total Bersih: Rp {data_hari['total_bersih']:,.0f}
⛽ Total Bensin: Rp {data_hari['total_bensin']:,.0f}
💳 Total Saldo: Rp {data_hari['total_saldo']:,.0f}
🏁 Total Kantong: Rp {data_hari['total_kantong']:,.0f}
"""

async def auto_reset(context: ContextTypes.DEFAULT_TYPE):
    reset_data()
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text="🔄 Tengah malam! Data harian sudah direset. Semangat narik hari ini! 🚀"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hallo Andhika! Kirim nomor HP pelanggan, aku langsung buatin link WA dan hitung alokasi tarif kamu. 🚀\n\n"
        "Ketik /rekap untuk lihat total hari ini.\n"
        "Ketik /reset untuk reset data manual."
    )
    return ConversationHandler.END

async def handle_nomor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = update.message.text.strip()
    if is_nomor_hp(teks):
        nomor = konversi_nomor(teks)
        link = f"https://wa.me/{nomor}?text={PESAN.replace(' ', '%20')}"
        await update.message.reply_text(link)
        await update.message.reply_text("Tarif berapa? (contoh: 15000)")
        return TUNGGU_TARIF
    else:
        await update.message.reply_text("Format nomor tidak dikenal. Coba kirim:\n085xxxxxxx\n+62 85xxxxxxx\n6285xxxxxxx")
        return ConversationHandler.END

async def handle_tarif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = re.sub(r'\D', '', update.message.text.strip())
    if not teks:
        await update.message.reply_text("Angka tidak valid, coba lagi.")
        return TUNGGU_TARIF
    tarif = int(teks)
    if tarif > 1000000:
        await update.message.reply_text("⚠️ Tarif terlalu besar, coba cek lagi.")
        return TUNGGU_TARIF
    hasil = hitung_tarif(tarif)
    await update.message.reply_text(hasil)
    return ConversationHandler.END

async def rekap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    n = len(data_hari["orders"])
    if n == 0:
        await update.message.reply_text("Belum ada order hari ini.")
        return ConversationHandler.END
    await update.message.reply_text(f"""
📊 Rekap Hari Ini ({n} order):
💵 Total Kotor: Rp {data_hari['total_kotor']:,.0f}
✂️ Total Potongan: Rp {data_hari['total_potongan']:,.0f}
✅ Total Bersih: Rp {data_hari['total_bersih']:,.0f}
⛽ Total Bensin: Rp {data_hari['total_bensin']:,.0f}
💳 Total Saldo: Rp {data_hari['total_saldo']:,.0f}
🏁 Total Kantong: Rp {data_hari['total_kantong']:,.0f}
""")
    return ConversationHandler.END

async def reset_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_data()
    await update.message.reply_text("✅ Data berhasil direset! Mulai hitung dari 0 lagi.")
    return ConversationHandler.END

app = ApplicationBuilder().token(TOKEN).build()

app.job_queue.run_daily(auto_reset, time=time(17, 0, 0))

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_nomor)],
    states={
        TUNGGU_TARIF: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tarif)],
    },
    fallbacks=[
        CommandHandler("start", start),
        CommandHandler("rekap", rekap),
        CommandHandler("reset", reset_manual),
    ],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("rekap", rekap))
app.add_handler(CommandHandler("reset", reset_manual))
app.add_handler(conv_handler)

print("Bot jalan...")
app.run_polling()
