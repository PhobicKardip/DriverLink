import re
import logging
import json
import aiohttp
from datetime import time, datetime, timedelta
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Makassar")
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

TOKEN = "8849663961:AAHDnl2ooXZGBovLkFEn7NPc_XdkX_F6QQ4"
PESAN = "Hallo ka,aku dari driver maxim"
CHAT_ID = 8036036520
KOTA_DEFAULT = "Palu"

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
    "history_makan": [],
    "history_pengeluaran": [],
    "total_saldo_keluar": 0,
}

# Riwayat mingguan (simpan per hari)
riwayat = []

# Pengaturan
setting = {
    "hitung_bensin": True,
    "hitung_saldo": True,
    "target_bensin": 25000,
    "target_saldo": 25000,
    "bensin_tercapai": False,
    "saldo_tercapai": False,
    "jenis_bbm": "pertalite",
    "harga_bbm": 10000,
    "konsumsi_km": 40,
}

HARGA_BBM = {
    "pertalite": 10000,
    "pertamax": 12300,
}

def reset_semua():
    # Simpan data hari ini ke riwayat sebelum reset
    if data["total_kotor"] > 0:
        riwayat.append({
            "tanggal": datetime.now(WIB).strftime("%d/%m/%Y"),
            "hari": datetime.now(WIB).strftime("%A"),
            "orders": len(data["orders"]),
            "total_kotor": data["total_kotor"],
            "total_bersih": data["total_bersih"],
            "total_kantong": data["total_kantong"],
        })
        # Simpan max 7 hari
        if len(riwayat) > 7:
            riwayat.pop(0)

    for key in data:
        if key in ["orders", "history_makan", "history_pengeluaran"]:
            data[key] = []
        else:
            data[key] = 0
    setting["bensin_tercapai"] = False
    setting["saldo_tercapai"] = False

def ekstrak_nomor(teks):
    kandidat = re.findall(r'(?:\+62|62|0)[\d\s\-]{8,17}', teks)
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

def hitung_tarif(tarif):
    komisi = tarif * 0.13
    sisa = tarif - komisi

    bensin = sisa * 0.10 if setting["hitung_bensin"] and not setting["bensin_tercapai"] else 0
    saldo = sisa * 0.10 if setting["hitung_saldo"] and not setting["saldo_tercapai"] else 0
    kantong = sisa - bensin - saldo

    data["orders"].append(tarif)
    data["total_kotor"] += tarif
    data["total_potongan"] += komisi
    data["total_bersih"] += sisa
    data["total_bensin"] += bensin
    data["total_saldo"] += saldo
    data["total_kantong"] += kantong

    n = len(data["orders"])

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

async def laporan_mingguan(context: ContextTypes.DEFAULT_TYPE):
    if not riwayat:
        await context.bot.send_message(chat_id=CHAT_ID, text="📊 Belum ada data minggu ini.")
        return

    total_kotor = sum(r["total_kotor"] for r in riwayat)
    total_bersih = sum(r["total_bersih"] for r in riwayat)
    total_kantong = sum(r["total_kantong"] for r in riwayat)
    total_orders = sum(r["orders"] for r in riwayat)
    hari_terbaik = max(riwayat, key=lambda x: x["total_kantong"])

    detail = "\n".join([
        f"📅 {r['tanggal']} — Rp {r['total_kantong']:,.0f} ({r['orders']} order)"
        for r in riwayat
    ])

    await context.bot.send_message(chat_id=CHAT_ID, text=f"""
📊 LAPORAN MINGGUAN

{detail}

━━━━━━━━━━━━━━━━
💵 Total Kotor: Rp {total_kotor:,.0f}
✅ Total Bersih: Rp {total_bersih:,.0f}
🏁 Total Kantong: Rp {total_kantong:,.0f}
🛵 Total Order: {total_orders}
🏆 Hari Terbaik: {hari_terbaik['tanggal']} (Rp {hari_terbaik['total_kantong']:,.0f})
""".strip())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
Hallo Andhika! 👋🏍

Selamat datang di OjolLink Bot — asisten pribadi driver Maxim kamu.

🔗 LINK WA OTOMATIS
Kirim nomor HP pelanggan dalam format apapun, bot langsung buatin link WA dengan pesan "Hallo dari Maxim" siap klik.

💰 KALKULATOR TARIF
Setelah dapat link, bot tanya tarif dan langsung hitung:
• Potongan aplikasi 13%
• Alokasi bensin & saldo
• Uang bersih kantong

📊 REKAP HARIAN
Semua order tercatat otomatis. Ketik /rekap kapanpun buat lihat total hari ini. Reset otomatis tiap tengah malam.

🌤 CUACA & BBM
Cek cuaca sebelum narik, hitung estimasi biaya bensin per perjalanan.

━━━━━━━━━━━━━━━━
Ketik /menu untuk lihat semua fitur.
Atau langsung kirim nomor HP pelanggan sekarang! 🚀
""".strip())
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

🛵 BBM & Jarak:
/setbbm — Pilih jenis BBM
/setkm [km/liter] — Set konsumsi motor
/jarak [km] — Hitung biaya bensin

🌤 Cuaca:
/cuaca — Cuaca Palu
/cuaca [kota] — Cuaca kota lain

Contoh:
/targetbensin 30000
/makan 15000
/setkm 40
/jarak 25
/cuaca Manado
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
            await update.message.reply_text(f"✅ Target bensin: Rp {int(nominal):,.0f}")
            return ConversationHandler.END
    await update.message.reply_text("Contoh: /targetbensin 30000")
    return ConversationHandler.END

async def set_target_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        nominal = re.sub(r'\D', '', context.args[0])
        if nominal:
            setting["target_saldo"] = int(nominal)
            setting["saldo_tercapai"] = False
            await update.message.reply_text(f"✅ Target saldo: Rp {int(nominal):,.0f}")
            return ConversationHandler.END
    await update.message.reply_text("Contoh: /targetsaldo 30000")
    return ConversationHandler.END

async def set_makan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        nominal = re.sub(r"\D", "", context.args[0])
        if nominal:
            jumlah = int(nominal)
            waktu = datetime.now(WIB).strftime("%H:%M")
            data["history_makan"].append({"waktu": waktu, "jumlah": jumlah, "kategori": "makan"})
            data["history_pengeluaran"].append({"waktu": waktu, "jumlah": jumlah, "alasan": "Makan"})
            data["total_makan"] += jumlah
            data["total_kantong"] -= jumlah

            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 History Makan", callback_data="history_makan"),
                InlineKeyboardButton("💸 Semua Pengeluaran", callback_data="history_pengeluaran"),
            ]])

            await update.message.reply_text(f"""
🍱 Pengeluaran makan dicatat!
💸 Rp {jumlah:,.0f} dikurangi dari kantong
Total makan: Rp {data['total_makan']:,.0f}
💰 Kantong bersih tersisa: Rp {data['total_kantong']:,.0f}
""".strip(), reply_markup=keyboard)
            return ConversationHandler.END
    await update.message.reply_text("Contoh: /makan 15000")
    return ConversationHandler.END

async def kurang_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) >= 2:
        nominal = re.sub(r"\D", "", context.args[0])
        alasan = " ".join(context.args[1:])
        if nominal:
            jumlah = int(nominal)
            waktu = datetime.now(WIB).strftime("%H:%M")
            data["history_pengeluaran"].append({"waktu": waktu, "jumlah": jumlah, "alasan": alasan})
            data["total_saldo_keluar"] += jumlah
            data["total_kantong"] -= jumlah

            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("💸 Semua Pengeluaran", callback_data="history_pengeluaran"),
            ]])

            await update.message.reply_text(f"""
💸 Pengeluaran dicatat!
📝 Alasan: {alasan}
💰 Rp {jumlah:,.0f} dikurangi dari kantong
💰 Kantong bersih tersisa: Rp {data['total_kantong']:,.0f}
""".strip(), reply_markup=keyboard)
            return ConversationHandler.END
    await update.message.reply_text("Contoh: /kurangsaldo 10000 beli air minum")
    return ConversationHandler.END

async def history_makan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["history_makan"]:
        await update.message.reply_text("Belum ada pengeluaran makan hari ini.")
        return ConversationHandler.END
    history_text = "\n".join([
        f"• {h['waktu']} - Rp {h['jumlah']:,.0f}"
        for h in data["history_makan"]
    ])
    await update.message.reply_text(f"""
🍱 History Makan Hari Ini:
{history_text}

Total makan: Rp {data['total_makan']:,.0f}
""".strip())
    return ConversationHandler.END

async def history_pengeluaran_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data["history_pengeluaran"]:
        await update.message.reply_text("Belum ada pengeluaran hari ini.")
        return ConversationHandler.END
    history_text = "\n".join([
        f"• {h['waktu']} - Rp {h['jumlah']:,.0f} ({h['alasan']})"
        for h in data["history_pengeluaran"]
    ])
    total = data["total_makan"] + data["total_saldo_keluar"]
    await update.message.reply_text(f"""
💸 Semua Pengeluaran Hari Ini:
{history_text}

Total pengeluaran: Rp {total:,.0f}
💰 Kantong bersih tersisa: Rp {data['total_kantong']:,.0f}
""".strip())
    return ConversationHandler.END

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "history_makan":
        if not data["history_makan"]:
            await query.edit_message_text("Belum ada pengeluaran makan hari ini.")
            return
        history_text = "\n".join([
            f"• {h['waktu']} - Rp {h['jumlah']:,.0f}"
            for h in data["history_makan"]
        ])
        await query.edit_message_text(f"""
🍱 History Makan Hari Ini:
{history_text}

Total makan: Rp {data['total_makan']:,.0f}
""".strip())
    elif query.data == "history_pengeluaran":
        if not data["history_pengeluaran"]:
            await query.edit_message_text("Belum ada pengeluaran hari ini.")
            return
        history_text = "\n".join([
            f"• {h['waktu']} - Rp {h['jumlah']:,.0f} ({h['alasan']})"
            for h in data["history_pengeluaran"]
        ])
        total = data["total_makan"] + data["total_saldo_keluar"]
        await query.edit_message_text(f"""
💸 Semua Pengeluaran Hari Ini:
{history_text}

Total pengeluaran: Rp {total:,.0f}
💰 Kantong bersih tersisa: Rp {data['total_kantong']:,.0f}
""".strip())

async def set_bbm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
Pilih jenis BBM:
1️⃣ /setbbm pertalite — Rp 10.000/liter
2️⃣ /setbbm pertamax — Rp 12.300/liter
""".strip())
    if context.args:
        jenis = context.args[0].lower()
        if jenis in HARGA_BBM:
            setting["jenis_bbm"] = jenis
            setting["harga_bbm"] = HARGA_BBM[jenis]
            await update.message.reply_text(f"✅ BBM diset ke {jenis.capitalize()} Rp {HARGA_BBM[jenis]:,.0f}/liter")
    return ConversationHandler.END

async def set_km(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        km = re.sub(r'\D', '', context.args[0])
        if km:
            setting["konsumsi_km"] = int(km)
            await update.message.reply_text(f"✅ Konsumsi motor: {km} km/liter")
            return ConversationHandler.END
    await update.message.reply_text("Contoh: /setkm 40")
    return ConversationHandler.END

async def hitung_jarak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        km = re.sub(r'\D', '', context.args[0])
        if km:
            jarak = int(km)
            liter = jarak / setting["konsumsi_km"]
            biaya = liter * setting["harga_bbm"]
            await update.message.reply_text(f"""
🛵 Estimasi BBM:
📍 Jarak: {jarak} km
⛽ BBM: {setting['jenis_bbm'].capitalize()} Rp {setting['harga_bbm']:,.0f}/liter
🔢 Konsumsi: {setting['konsumsi_km']} km/liter
💧 Kebutuhan: {liter:.2f} liter
💰 Biaya: Rp {biaya:,.0f}
""".strip())
            return ConversationHandler.END
    await update.message.reply_text("Contoh: /jarak 25")
    return ConversationHandler.END

async def cuaca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kota = "+".join(context.args) if context.args else KOTA_DEFAULT
    try:
        url = f"https://wttr.in/{kota}?format=3&lang=id"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"User-Agent": "curl/7.68.0"}) as resp:
                if resp.status == 200:
                    teks = await resp.text()
                    await update.message.reply_text(f"🌤 {teks.strip()}")
                else:
                    await update.message.reply_text(f"Kota tidak ditemukan. Coba nama kota lain.")
    except Exception:
        await update.message.reply_text("Gagal ambil data cuaca. Coba lagi nanti.")
    return ConversationHandler.END

app = ApplicationBuilder().token(TOKEN).build()

# Reset tiap tengah malam WIB = 17.00 UTC
app.job_queue.run_daily(auto_reset, time=time(17, 0, 0))
# Laporan mingguan tiap Senin pagi jam 07.00 WIB = 23.00 UTC Minggu
app.job_queue.run_daily(laporan_mingguan, time=time(23, 0, 0), days=(6,))

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
        CommandHandler("kurangsaldo", kurang_saldo),
        CommandHandler("historymakan", history_makan_cmd),
        CommandHandler("historypengeluaran", history_pengeluaran_cmd),
        CommandHandler("setbbm", set_bbm),
        CommandHandler("setkm", set_km),
        CommandHandler("jarak", hitung_jarak),
        CommandHandler("cuaca", cuaca),
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
app.add_handler(CommandHandler("kurangsaldo", kurang_saldo))
app.add_handler(CommandHandler("historymakan", history_makan_cmd))
app.add_handler(CommandHandler("historypengeluaran", history_pengeluaran_cmd))
app.add_handler(CommandHandler("setbbm", set_bbm))
app.add_handler(CommandHandler("setkm", set_km))
app.add_handler(CommandHandler("jarak", hitung_jarak))
app.add_handler(CommandHandler("cuaca", cuaca))
app.add_handler(CallbackQueryHandler(callback_handler))
app.add_handler(conv_handler)

print("Bot jalan...")
app.run_polling()
