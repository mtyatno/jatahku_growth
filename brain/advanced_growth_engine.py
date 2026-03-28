import sys
import os
import requests
import feedparser
from pytrends.request import TrendReq
from googleapiclient.discovery import build
from google import genai
from datetime import datetime

# Panggil config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Inisialisasi AI
client = genai.Client(api_key=config.GEMINI_API_KEY)

# ==========================================
# 1. DATA SOURCES (FETCHERS)
# ==========================================
def fetch_reddit():
    print("Menggali r/personalfinance, r/povertyfinance, r/Frugal...")
    urls = [
        "https://www.reddit.com/r/personalfinance/.rss",
        "https://www.reddit.com/r/povertyfinance/.rss",
        "https://www.reddit.com/r/Frugal/.rss"
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    reddit_data = []
    
    for url in urls:
        try:
            # Gunakan requests untuk pass header, lalu parse dengan feedparser
            response = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(response.content)
            for entry in feed.entries[:10]: # Ambil 10 terbaru per sub
                reddit_data.append({
                    "source": "Reddit",
                    "title": entry.title,
                    "link": entry.link,
                    "text_length": len(entry.title)
                })
        except Exception as e:
            print(f"❌ Error Reddit RSS ({url}): {e}")
    return reddit_data

def fetch_trends():
    print("Mengecek Google Trends Indonesia (via RSS)...")
    trends_data = []
    try:
        # Jalur tikus RSS resmi Google Trends untuk Indonesia
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=ID"
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            keyword = entry.title
            trends_data.append({
                "source": "Google Trends",
                "title": keyword,
                "link": entry.link,
                "text_length": len(keyword)
            })
    except Exception as e:
        print(f"❌ Error Google Trends RSS: {e}")
    return trends_data
def fetch_youtube():
    print("Mencari sinyal di YouTube...")
    youtube_data = []
    if not hasattr(config, 'YOUTUBE_API_KEY') or config.YOUTUBE_API_KEY == "PASTE_API_KEY_YOUTUBE_DI_SINI":
        print("⚠️ YouTube API Key belum disetup. Melewati YouTube...")
        return youtube_data

    try:
        youtube = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY)
        queries = ["cara hemat uang", "gaji habis", "utang"]
        
        for q in queries:
            request = youtube.search().list(q=q, part='snippet', type='video', maxResults=5)
            response = request.execute()
            
            for item in response['items']:
                youtube_data.append({
                    "source": "YouTube",
                    "title": item['snippet']['title'],
                    "link": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                    "text_length": len(item['snippet']['title'])
                })
    except Exception as e:
        print(f"❌ Error YouTube API: {e}")
    return youtube_data

# ==========================================
# 2. FILTER DATA
# ==========================================
def filter_data(raw_data):
    keywords = ["broke", "salary", "debt", "budget", "spending", "save", "paycheck", 
                "gaji", "utang", "boros", "hemat", "tabungan"]
    
    filtered = []
    for item in raw_data:
        title_lower = item['title'].lower()
        if any(kw in title_lower for kw in keywords):
            filtered.append(item)
    return filtered

# ==========================================
# 3. SCORING SYSTEM
# ==========================================
def score_data(filtered_data):
    scored = []
    for item in filtered_data:
        score = 0
        title_lower = item['title'].lower()
        
        # Aturan Scoring
        if any(kw in title_lower for kw in ["broke", "gaji habis", "gaji"]): score += 3
        if any(kw in title_lower for kw in ["debt", "utang"]): score += 3
        if any(kw in title_lower for kw in ["help", "struggle"]): score += 2
        if any(kw in title_lower for kw in ["budget", "hemat"]): score += 2
        
        if item['text_length'] > 60: score += 1
        if item['source'] == "Google Trends": score += 3
        
        item['score'] = score
        scored.append(item)
    
    # Urutkan berdasarkan skor tertinggi
    return sorted(scored, key=lambda x: x['score'], reverse=True)

# ==========================================
# 4. CLUSTERING
# ==========================================
def cluster_data(scored_data):
    clusters = {
        "Gaji habis": [],
        "Utang": [],
        "Boros / gaya hidup": [],
        "Tidak tahu sisa uang": []
    }
    
    for item in scored_data:
        t = item['title'].lower()
        if "gaji" in t or "broke" in t or "paycheck" in t:
            clusters["Gaji habis"].append(item)
        elif "utang" in t or "debt" in t:
            clusters["Utang"].append(item)
        elif "boros" in t or "spending" in t:
            clusters["Boros / gaya hidup"].append(item)
        else:
            clusters["Tidak tahu sisa uang"].append(item)
            
    return clusters

# ==========================================
# 6. GENERATE CONTENT (AI)
# ==========================================
def generate_content(title):
    prompt = f"""
    Buatkan script video TikTok singkat berdasarkan pain point ini: "{title}"
    
    Gunakan gaya bahasa Indonesia gaul, tajam, dan relatable. 
    Format WAJIB persis seperti ini:
    HOOK: [Kalimat pendek, kuat, menohok]
    RELATE: [Kalimat yang bikin merasa 'ini gue banget']
    SOLUSI: [Jelaskan masalah ini karena gak ada sistem, arahkan pakai JatahkuBot Telegram untuk ngatur uang harian]
    CTA: [Ajak klik link di bio untuk coba gratis jatahku.com]
    
    Hanya output format di atas, tanpa awalan atau akhiran.
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"Gagal generate AI: {e}"

# ==========================================
# 7 & 8. OUTPUT & TELEGRAM SENDER
# ==========================================
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": config.TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
        print("✅ Laporan terkirim ke Telegram!")
    except Exception as e:
        print(f"❌ Gagal kirim Telegram: {e}")

def main():
    print("🚀 MEMULAI JATAHKU ADVANCED GROWTH ENGINE...")
    
    # Pipeline Eksekusi
    raw = fetch_reddit() + fetch_trends() + fetch_youtube()
    filtered = filter_data(raw)
    scored = score_data(filtered)
    
    if not scored:
        send_to_telegram("⚠️ Growth Engine berjalan, tapi tidak ada sinyal kuat hari ini.")
        return

    # Ambil Top 5
    top_signals = scored[:5]
    clusters = cluster_data(scored)
    
    # Hitung statistik cluster untuk header
    cluster_stats = ""
    for c_name, c_list in clusters.items():
        if len(c_list) > 0:
            cluster_stats += f"- {c_name} ({len(c_list)} data)\n"

    # Generate Script untuk Top 1 Signal
    best_signal = top_signals[0]
    print(f"Mengolah AI untuk Top Signal: {best_signal['title']}...")
    ai_script = generate_content(best_signal['title'])

    # Susun Laporan Akhir
    # Siapkan string untuk signal ke-2 agar rapi
    signal_2 = f"2. [{top_signals[1]['score']} pts] {top_signals[1]['title']} <i>({top_signals[1]['source']})</i>" if len(top_signals) > 1 else ""

    # Susun Laporan Akhir
    report = f"""🚀 <b>GROWTH SIGNAL REPORT</b> 🚀
<i>{datetime.now().strftime('%d %B %Y')}</i>

📊 <b>Top Issue Hari Ini:</b>
{cluster_stats}
🔥 <b>Top Signals (Scored):</b>
1. [{best_signal['score']} pts] {best_signal['title']} <i>({best_signal['source']})</i>
{signal_2}

🎬 <b>SCRIPT OF THE DAY:</b>
<i>Berdasarkan issue nomor 1</i>

{ai_script}

<i>~ Mesin Growth V2.0 (Legal Multi-Source)</i>
"""
    
    print("\n" + report)
    send_to_telegram(report)

if __name__ == "__main__":
    main()
