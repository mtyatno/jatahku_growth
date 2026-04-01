import sys
import os
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from google import genai

# Panggil config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from memory import topic_history

# Inisialisasi AI
client = genai.Client(api_key=config.GEMINI_API_KEY)

FRESHNESS_HOURS = 72  # Abaikan sinyal lebih lama dari 72 jam

# Rotasi cluster harian — berputar setiap 4 hari
# Senin=0, Selasa=1, Rabu=2, Kamis=3, Jumat=4, dst.
CLUSTER_ROTATION = ["Gaji habis", "Utang", "Boros / gaya hidup", "Tidak tahu sisa uang"]

def get_todays_cluster():
    """Paksa cluster berbeda tiap hari berdasarkan hari ke-N."""
    day_index = datetime.now().timetuple().tm_yday
    cluster = CLUSTER_ROTATION[day_index % len(CLUSTER_ROTATION)]
    print(f"📅 Cluster hari ini (rotasi): {cluster}")
    return cluster


def _is_fresh(published_str):
    if not published_str:
        return True
    try:
        pub_dt = parsedate_to_datetime(published_str)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=FRESHNESS_HOURS)
        return pub_dt >= cutoff
    except Exception:
        return True


# ==========================================
# 1. DATA SOURCES (FETCHERS)
# ==========================================
def fetch_reddit():
    print("Menggali Reddit (finansial, povertyfinance, Frugal, keuangan)...")
    urls = [
        "https://www.reddit.com/r/personalfinance/.rss",
        "https://www.reddit.com/r/povertyfinance/.rss",
        "https://www.reddit.com/r/Frugal/.rss",
        "https://www.reddit.com/r/finansial/.rss",
        "https://www.reddit.com/r/keuangan/.rss",
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    reddit_data = []

    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(response.content)
            for entry in feed.entries[:10]:
                published = getattr(entry, 'published', None)
                if not _is_fresh(published):
                    continue
                reddit_data.append({
                    "source": "Reddit",
                    "title": entry.title,
                    "link": entry.link,
                    "text_length": len(entry.title),
                    "published": published or ""
                })
        except Exception as e:
            print(f"❌ Error Reddit RSS ({url}): {e}")
    return reddit_data


def fetch_trends():
    print("Mengecek Google Trends Indonesia (via RSS)...")
    trends_data = []
    try:
        url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=ID"
        feed = feedparser.parse(url)
        for entry in feed.entries:
            trends_data.append({
                "source": "Google Trends",
                "title": entry.title,
                "link": entry.link,
                "text_length": len(entry.title),
                "published": getattr(entry, 'published', "")
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
        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY)
        queries = ["cara hemat uang", "gaji habis", "utang", "boros", "tabungan"]

        for q in queries:
            request = youtube.search().list(q=q, part='snippet', type='video', maxResults=5,
                                            publishedAfter=(datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%SZ'))
            response = request.execute()
            for item in response['items']:
                youtube_data.append({
                    "source": "YouTube",
                    "title": item['snippet']['title'],
                    "link": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                    "text_length": len(item['snippet']['title']),
                    "published": item['snippet'].get('publishedAt', "")
                })
    except Exception as e:
        print(f"❌ Error YouTube API: {e}")
    return youtube_data


# ==========================================
# 2. FILTER DATA
# ==========================================
def filter_data(raw_data):
    keywords = ["broke", "salary", "debt", "budget", "spending", "save", "paycheck",
                "gaji", "utang", "boros", "hemat", "tabungan", "cicilan", "kredit",
                "nabung", "financial", "uang", "money", "invest"]

    filtered = []
    for item in raw_data:
        title_lower = item['title'].lower()
        if any(kw in title_lower for kw in keywords):
            # Buang yang sudah dipakai 7 hari terakhir
            if not topic_history.is_duplicate(item['title']):
                filtered.append(item)
            else:
                print(f"🔁 Skip duplikat: {item['title'][:60]}...")
    return filtered


# ==========================================
# 3. SCORING SYSTEM
# ==========================================
def score_data(filtered_data, target_cluster):
    """Score data dengan bonus tambahan jika cocok dengan cluster rotasi hari ini."""
    cluster_keywords = {
        "Gaji habis":          ["broke", "gaji", "gaji habis", "paycheck", "habis"],
        "Utang":               ["debt", "utang", "cicilan", "kredit", "pinjam"],
        "Boros / gaya hidup":  ["boros", "spending", "lifestyle", "jajan", "belanja", "impuls"],
        "Tidak tahu sisa uang":["budget", "hemat", "tabungan", "nabung", "sisa", "save"],
    }
    target_kws = cluster_keywords.get(target_cluster, [])

    scored = []
    for item in filtered_data:
        score = 0
        title_lower = item['title'].lower()

        # Skor dasar
        if any(kw in title_lower for kw in ["broke", "gaji habis", "gaji"]): score += 3
        if any(kw in title_lower for kw in ["debt", "utang", "cicilan"]):    score += 3
        if any(kw in title_lower for kw in ["help", "struggle", "susah"]):   score += 2
        if any(kw in title_lower for kw in ["budget", "hemat", "nabung"]):   score += 2
        if item['text_length'] > 60:                                          score += 1
        if item['source'] == "Google Trends":                                 score += 2  # turun dari 3

        # Bonus cluster rotasi hari ini (+4 poin)
        if any(kw in title_lower for kw in target_kws):
            score += 4
            item['cluster_match'] = True
        else:
            item['cluster_match'] = False

        item['score'] = score
        scored.append(item)

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
        elif "utang" in t or "debt" in t or "cicilan" in t:
            clusters["Utang"].append(item)
        elif "boros" in t or "spending" in t or "jajan" in t:
            clusters["Boros / gaya hidup"].append(item)
        else:
            clusters["Tidak tahu sisa uang"].append(item)

    return clusters


# ==========================================
# 5. GENERATE CONTENT (AI)
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
# 6. TELEGRAM SENDER
# ==========================================
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": config.TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
        print("✅ Laporan terkirim ke Telegram!")
    except Exception as e:
        print(f"❌ Gagal kirim Telegram: {e}")


# ==========================================
# MAIN
# ==========================================
def main():
    print("🚀 MEMULAI JATAHKU ADVANCED GROWTH ENGINE V3.0...")

    # Tentukan cluster hari ini (rotasi paksa)
    todays_cluster = get_todays_cluster()

    # Pipeline Eksekusi
    raw = fetch_reddit() + fetch_trends() + fetch_youtube()
    filtered = filter_data(raw)
    scored = score_data(filtered, todays_cluster)

    if not scored:
        msg = f"⚠️ Growth Engine berjalan, tapi tidak ada sinyal baru hari ini (cluster: {todays_cluster})."
        send_to_telegram(msg)
        return

    # Ambil Top 5
    top_signals = scored[:5]
    clusters = cluster_data(scored)

    # Statistik cluster
    cluster_stats = ""
    for c_name, c_list in clusters.items():
        if c_list:
            cluster_stats += f"- {c_name} ({len(c_list)} data)\n"

    # Generate Script untuk Top 1 Signal
    best_signal = top_signals[0]
    print(f"Mengolah AI untuk Top Signal: {best_signal['title']}...")
    ai_script = generate_content(best_signal['title'])

    # Simpan ke riwayat agar tidak muncul lagi minggu ini
    topic_history.save(best_signal['title'], todays_cluster)
    print(f"💾 Topik tersimpan ke riwayat: {best_signal['title'][:60]}")

    # Signal ke-2 (jika ada)
    signal_2 = ""
    if len(top_signals) > 1:
        s2 = top_signals[1]
        signal_2 = f"2. [{s2['score']} pts] {s2['title']} <i>({s2['source']})</i>"

    # Susun Laporan Akhir
    report = f"""🚀 <b>GROWTH SIGNAL REPORT</b> 🚀
<i>{datetime.now().strftime('%d %B %Y')}</i>
🎯 <b>Cluster Fokus Hari Ini:</b> {todays_cluster}

📊 <b>Top Issue:</b>
{cluster_stats}
🔥 <b>Top Signals (Scored):</b>
1. [{best_signal['score']} pts] {best_signal['title']} <i>({best_signal['source']})</i>
{signal_2}

🎬 <b>SCRIPT OF THE DAY:</b>
<i>Berdasarkan issue nomor 1</i>

{ai_script}

<i>~ Mesin Growth V3.0 | Anti-Repeat + Cluster Rotation</i>
"""

    print("\n" + report)
    send_to_telegram(report)


if __name__ == "__main__":
    main()
