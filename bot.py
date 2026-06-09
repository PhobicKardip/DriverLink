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

# Data harian
data = {
    "orders": [],
    "total_kotor": 0,
    "total_potongan": 0,
    "total_bersih": 0,
    "total_bensin": 0,
    "total_saldo": 0,
    "total_kantong": 0,
    "total_makan": 0,
}

# Pengaturan
setting = {
    "hitung_bensin": True,
    "hitung_saldo": True,
    "target_bensin": 25000,
    "target_saldo": 25000,
    "uang_makan": 0,
    "bensin_tercapai": False,
    "saldo_tercapai": False,
}

def reset_semua():
    for key in data:
        data[key] = [] if key == "orders" else 0
    setting["bensin_tercapai"] = False
    setting["saldo_tercapai"] = False

def ekstrak_nomor(teks):
    # Cari semua angka yang kemungkinan nomor HP
    kandidat = re.findall(r'[\+62|62|0][\d\s\-]{8,17}', teks)
    for k in kandidat:
        nomor = re.sub(r'[\s\-\(\)\+]', '', k)
        nomor = re.sub(r'\D', '', nomor)
        if nomor.startswith('62'):
            pass
        elif nomor.startswith('0'):
            nomor = '62' + nomor[1:]
        else:
            continue
        if 10 <= len(nomor) <= 15:
            return nomor
    return None

def is_nomor_hp(teks):
    return ekstrak_nomor(teks) is not None

def hitung_tarif(tarif):
    komisi = tarif * 0.13
    sisa = tarif - komisi

    bensin = sisa * 0.10 if setting["hitung_bensin"] and not setting["bensin_tercapai"] else 0
    saldo = sisa * 0.10 if setting["hitung_saldo"] and not setting["saldo_tercapai"] else 0
    kantong = sisa - bensin - saldo
    makan = setting["uang_makan"]
    kantong_bersih = kantong - makan

    data["orders"].append(tarif)
    data["total_kotor"] += tarif
    data["total_potongan"] += komisi
    data["total_bersih"] += sisa
    data["total_bensin"] += bensin
    data["total_saldo"] += saldo
    data["total_kantong"] += kantong_bersih
    data["total_makan"] += makan

    n = len(data["orders"])

    # Cek apakah target tercapai
    notif_bensin = ""
    notif_saldo = ""
    if setting["hitung_bensin"] and not setting["bensin_tercapai"] and data["total_bensin"] >= setting["target_bensin"]:
        setting["bensin_tercapai"] = True
        notif_bensin = f"\n⛽ Tabungan bensin TERCAPAI! Rp {setting['target_bensin']:,.0f} ✅"
    if setting["hitung_saldo"] and not setting["saldo_tercapai"] and data["total_saldo"] >= setting["target_saldo"]:
        setting["saldo_tercapai"] = True
        notif_saldo = f"\n💳 Tabungan saldo TERCAPAI! Rp {setting['target_saldo']:,.0f} ✅"

    status_bensin = "⏸ nonaktif" if not setting["hitung_bensin"] else ("✅ tercapai" if setting["bensin_tercapai"] else f"Rp {data['total_bensin']:,.0f} / Rp {setting['target_bensin']:,.0f}")
    status_saldo = "⏸ nonaktif" if not setting["hitung_saldo"] else ("✅ tercapai" if setting["saldo_tercapai"] else f"Rp {data['total_saldo']:,.0f} / Rp {setting['target_saldo']:,.0f}")

    makan_line = f"\n🍱 Uang makan: -Rp {makan:,.0f}" if makan > 0 else ""

    return f"""
💰 Tarif Masuk: Rp {tarif:,.0f}
✂️ Potongan Apk (13%): -Rp {komisi:,.0f}
Sisa Bersih Aplikasi: Rp {sisa:,.0f}

📥 Alokasi:
⛽ Bensin: Rp {bensin:,.0f}
💳 Saldo: Rp {saldo:,.0f}{makan_line}
🏁 KANTONG BERSIH: Rp {kantong_bersih:,.0f}
{notif_bensin}{notif_saldo}
━━━━━━━━━━━━━━━━
📊 Rekap Hari Ini ({n} order):
💵 Total Kotor: Rp {data['total_kotor']:,.0f}
✂️ Total Potongan: Rp {data['total_potongan']:,.0f}
✅ Total Bersih: Rp {data['total_bersih']:,.0f}
⛽ Bensin: {status_bensin}
💳 Saldo: {status_saldo}
🏁 Total Kantong: Rp {data['total_kantong']:,.0f}
""".strip()

async def auto_reset(context: ContextTypes.DEFAULT_TYPE):
    reset_semua()
    await context.bot.send_message(chat_id=CHAT_ID, text="🔄 Tengah malam! Data harian sudah direset. Semangat narik hari ini! 🚀")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hallo Andhika! 👋\n\nKirim nomor HP pelanggan → dapat link WA + hitung tarif otomatis.\n\nKetik /help untuk lihat semua fitur."
    )
    return ConversationHandler.END

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
📋 DAFTAR COMMAND

📊 Data:
/rekap — Lihat total hari ini
/reset — Reset semua data

⛽ Bensin:
/resetbensin — Reset tabungan bensin
/bensin — Toggle hitung bensin on/off
/targetbensin [nominal] — Set target bensin

💳 Saldo:
/resetsaldo — Reset tabungan saldo
/saldo — Toggle hitung saldo on/off
/targetsaldo [nominal] — Set target saldo

🍱 Pengeluaran:
/makan [nominal] — Set uang makan

Contoh:
/targetbensin 30000
/makan 15000
""".strip())
    return ConversationHandler.END

async def handle_nomor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = update.message.text.strip()
    nomor = ekstrak_nomor(teks)
    if nomor:
        link = f"https://wa.me/{nomor}?text={PESAN.replace(' ', '%20')}"
        await update.message.reply_text(link)
        await update.message.reply_text("Tarif berapa? (contoh: 15000)")
        return TUNGGU_TARIF
    else:
        await update.message.reply_text("Format nomor tidak dikenal. Coba kirim nomor HP pelanggan.")
        return ConversationHandler.END

async def handle_tarif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teks = re.sub(r'\D', '', update.message.text.strip())
    if not teks:
        await update.message.reply_text("Angka tidak valid, coba lagi.")
        return TUNGGU_TARIF
    tarif = int(teks)
    if tarif > 500000:
        await update.message.reply_text("⚠️ Tarif terlalu besar, coba cek lagi.")
        return TUNGGU_TARIF
    hasil = hitung_tarif(tarif)
    await update.message.reply_text(hasil)
    return ConversationHandler.END

async def rekap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    n = len(data["orders"])
    if n == 0:
        await update.message.reply_text("Belum ada order hari ini.")
        return ConversationHandler.END
    status_bensin = "⏸ nonaktif" if not setting["hitung_bensin"] else ("✅ tercapai" if setting["bensin_tercapai"] else f"Rp {data['total_bensin']:,.0f} / Rp {setting['target_bensin']:,.0f}")
    status_saldo = "⏸ nonaktif" if not setting["hitung_saldo"] else ("✅ tercapai" if setting["saldo_tercapai"] else f"Rp {data['total_saldo']:,.0f} / Rp {setting['target_saldo']:,.0f}")
    await update.message.reply_text(f"""
📊 Rekap Hari Ini ({n} order):
💵 Total Kotor: Rp {data['total_kotor']:,.0f}
✂️ Total Potongan: Rp {data['total_potongan']:,.0f}
✅ Total Bersih: Rp {data['total_bersih']:,.0f}
⛽ Bensin: {status_bensin}
💳 Saldo: {status_saldo}
🍱 Total Makan: Rp {data['total_makan']:,.0f}
🏁 Total Kantong: Rp {data['total_kantong']:,.0f}
""".strip())
    return ConversationHandler.END

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_semua()
    await update.message.reply_text("✅ Semua data direset!")
    return ConversationHandler.END

async def reset_bensin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data["total_bensin"] = 0
    setting["bensin_tercapai"] = False
    await update.message.reply_text("✅ Tabungan bensin direset!")
    return ConversationHandler.END

async def reset_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data["total_saldo"] = 0
    setting["saldo_tercapai"] = False
    await update.message.reply_text("✅ Tabungan saldo direset!")
    return ConversationHandler.END

async def toggle_bensin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    setting["hitung_bensin"] = not setting["hitung_bensin"]
    status = "✅ aktif" if setting["hitung_bensin"] else "⏸ nonaktif"
    await update.message.reply_text(f"⛽ Hitung bensin sekarang: {status}")
    return ConversationHandler.END

async def toggle_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    setting["hitung_saldo"] = not setting["hitung_saldo"]
    status = "✅ aktif" if setting["hitung_saldo"] else "⏸ nonaktif"
    await update.message.reply_text(f"💳 Hitung saldo sekarang: {status}")
    return ConversationHandler.END

async def set_target_bensin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        nominal = re.sub(r'\D', '', context.args[0])
        if nominal:
            setting["target_bensin"] = int(nominal)
            setting["bensin_tercapai"] = False
            await update.message.reply_text(f"✅ Target bensin diset ke Rp {int(nominal):,.0f}")
            return ConversationHandler.END
    await update.message.reply_text("Contoh: /targetbensin 30000")
    return ConversationHandler.END

async def set_target_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        nominal = re.sub(r'\D', '', context.args[0])
        if nominal:
            setting["target_saldo"] = int(nominal)
            setting["saldo_tercapai"] = False
            await update.message.reply_text(f"✅ Target saldo diset ke Rp {int(nominal):,.0f}")
            return ConversationHandler.END
    await update.message.reply_text("Contoh: /targetsaldo 30000")
    return ConversationHandler.END

async def set_makan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        nominal = re.sub(r'\D', '', context.args[0])
        if nominal:
            setting["uang_makan"] = int(nominal)
            await update.message.reply_text(f"✅ Uang makan diset ke Rp {int(nominal):,.0f}")
            return ConversationHandler.END
    await update.message.reply_text("Contoh: /makan 15000")
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
        CommandHandler("help", help_cmd),
        CommandHandler("menu", help_cmd),
        CommandHandler("rekap", rekap),
        CommandHandler("reset", reset_cmd),
        CommandHandler("resetbensin", reset_bensin),
        CommandHandler("resetsaldo", reset_saldo),
        CommandHandler("bensin", toggle_bensin),
        CommandHandler("saldo", toggle_saldo),
        CommandHandler("targetbensin", set_target_bensin),
        CommandHandler("targetsaldo", set_target_saldo),
        CommandHandler("makan", set_makan),
    ],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("menu", help_cmd))
app.add_handler(CommandHandler("rekap", rekap))
app.add_handler(CommandHandler("reset", reset_cmd))
app.add_handler(CommandHandler("resetbensin", reset_bensin))
app.add_handler(CommandHandler("resetsaldo", reset_saldo))
app.add_handler(CommandHandler("bensin", toggle_bensin))
app.add_handler(CommandHandler("saldo", toggle_saldo))
app.add_handler(CommandHandler("targetbensin", set_target_bensin))
app.add_handler(CommandHandler("targetsaldo", set_target_saldo))
app.add_handler(CommandHandler("makan", set_makan))
app.add_handler(conv_handler)

print("Bot jalan...")
app.run_polling()
