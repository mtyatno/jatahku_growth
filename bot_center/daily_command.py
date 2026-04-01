# bot_center/daily_command.py
import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from scraper.trend_scraper import get_daily_ideas
from brain.script_generator import generate_viral_script
from memory import topic_history


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Pesan beserta AI Script berhasil dikirim ke Telegram!")
    except Exception as e:
        print(f"❌ Gagal mengirim pesan: {e}")


def pick_fresh_idea(ideas):
    """Pilih ide pertama yang belum pernah dipakai 7 hari terakhir."""
    for idea_line in ideas:
        # Hapus nomor urut di depan ("1. ", "2. ", dst)
        idea = idea_line.split(". ", 1)[-1]
        if not topic_history.is_duplicate(idea):
            return idea
    # Semua duplikat — pakai yang pertama tetap (tapi catat)
    print("⚠️ Semua ide adalah duplikat, terpaksa pakai ide pertama.")
    return ideas[0].split(". ", 1)[-1]


def main():
    print("Mengeksekusi Growth Engine...")

    # 1. Ambil data mentah dari scraper (sudah difilter duplikat di dalamnya)
    ideas = get_daily_ideas()
    ideas_text = "\n".join(ideas)

    # 2. Pilih ide segar (skip yang sudah dipakai minggu ini)
    top_idea = pick_fresh_idea(ideas)
    print(f"Membuat script untuk ide: {top_idea}")
    ai_script = generate_viral_script(top_idea)

    # 3. Simpan ke riwayat supaya tidak muncul lagi minggu ini
    topic_history.save(top_idea)
    print(f"💾 Topik tersimpan ke riwayat.")

    # 4. Susun Laporan Harian untuk Telegram
    message = f"""
🚀 <b>JATAHKU GROWTH COMMAND</b> 🚀

📊 <b>Status Sistem:</b> <i>Online & Running</i>

💡 <b>Ide Konten Hari Ini:</b>
{ideas_text}

🎬 <b>SCRIPT OF THE DAY (Siap Rekam):</b>
<i>Angle: {top_idea}</i>

{ai_script}

<i>~ Mesin Growth V3.0 | Jatahku.com</i>
"""

    # 5. Kirim laporan ke Telegram
    send_telegram_message(message)


if __name__ == "__main__":
    main()
