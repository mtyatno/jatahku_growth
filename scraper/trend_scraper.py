# scraper/trend_scraper.py
import requests
import xml.etree.ElementTree as ET
import sys
import os
from apify_client import ApifyClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def get_reddit_ideas():
    """Mengambil curhatan dari r/finansial via RSS Feed (Jalur Bypass 403)"""
    url = "https://www.reddit.com/r/finansial/new.rss"
    # Tetap menyamar sebagai browser agar lolos dari blokir basic
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    ideas = []
    
    try:
        print("Mencoba menembus Reddit via RSS...")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Parsing format XML/RSS bawaan Reddit
            root = ET.fromstring(response.content)
            # Namespace Atom yang dipakai Reddit
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', ns)
            
            # Ambil 3 curhatan terbaru
            for entry in entries[:3]: 
                title = entry.find('atom:title', ns).text
                ideas.append(f"[REDDIT] {title}")
            print("✅ Reddit RSS berhasil ditembus!")
        else:
            print(f"❌ Reddit RSS ditolak. Status Code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error scraping Reddit RSS: {e}")
        
    return ideas

def get_apify_ideas():
    """Mengambil tren X/TikTok (Fallback jika belum ada Actor berbayar)"""
    if not hasattr(config, 'APIFY_API_TOKEN') or config.APIFY_API_TOKEN == "PASTE_TOKEN_APIFY_DI_SINI":
        return []
        
    # Karena API Twitter gratisan sering bermasalah, kita set fallback sementara 
    # sampai Mas menemukan Actor gratisan di Apify yang cocok.
    return []

def get_daily_ideas():
    print("Mencari ide konten untuk Jatahku Growth Engine...")
    reddit_ideas = get_reddit_ideas()
    apify_ideas = get_apify_ideas()
    
    all_ideas = reddit_ideas + apify_ideas
    
    if not all_ideas:
        print("⚠️ Semua scraper gagal, menggunakan ide darurat.")
        all_ideas = ["[SISTEM] Gaji 5 juta tapi tiap hari ngopi 50rb"]
        
    formatted_ideas = []
    for i, idea in enumerate(all_ideas[:5], 1):
        formatted_ideas.append(f"{i}. {idea}")
        
    return formatted_ideas

if __name__ == "__main__":
    hasil = get_daily_ideas()
    print("\n--- HASIL TANGKAPAN HARI INI ---")
    for h in hasil:
        print(h)
