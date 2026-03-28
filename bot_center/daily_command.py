# bot_center/daily_command.py
import requests
import sys
import os

# Menambahkan root folder ke sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from scraper.trend_scraper import get_daily_ideas
from brain.script_generator import generate_viral_script

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

def main():
    print("Mengeksekusi Growth Engine...")
    
    # 1. Ambil data mentah dari scraper
    ideas = get_daily_ideas()
    ideas_text = "\n".join(ideas)
    
    # 2. Ambil ide pertama sebagai "Top Idea" dan proses ke AI
    top_idea = ideas[0].split(". ", 1)[-1] # Membersihkan angka di depan ide
    print(f"Membuat script untuk ide: {top_idea}")
    ai_script = generate_viral_script(top_idea)
    
    # 3. Susun Laporan Harian untuk Telegram
    message = f"""
🚀 <b>JATAHKU GROWTH COMMAND</b> 🚀

📊 <b>Status Sistem:</b> <i>Online & Running</i>

💡 <b>Ide Konten Hari Ini:</b>
{ideas_text}

🎬 <b>SCRIPT OF THE DAY (Siap Rekam):</b>
<i>Angle: {top_idea}</i>

{ai_script}

<i>~ Mesin Growth V1.0 | Jatahku.com</i>
"""
    
    # 4. Kirim laporan ke Telegram Mas Yatno
    send_telegram_message(message)

if __name__ == "__main__":
    main()
