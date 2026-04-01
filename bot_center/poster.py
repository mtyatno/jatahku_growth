# bot_center/poster.py — Kirim post ke X (Twitter) dan Meta Threads
import sys
import os
import time
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def post_to_x(text):
    """Post ke X menggunakan Twitter API v2 dengan OAuth 1.0a (via tweepy)."""
    import tweepy
    client = tweepy.Client(
        consumer_key=config.X_API_KEY,
        consumer_secret=config.X_API_SECRET,
        access_token=config.X_ACCESS_TOKEN,
        access_token_secret=config.X_ACCESS_SECRET
    )
    response = client.create_tweet(text=text)
    tweet_id = response.data['id']
    return f"https://x.com/i/web/status/{tweet_id}"


def post_to_threads(text):
    """Post ke Meta Threads menggunakan Graph API."""
    base = f"https://graph.threads.net/v1.0/{config.THREADS_USER_ID}"

    # Step 1: Buat container
    r = requests.post(
        f"{base}/threads",
        params={
            "media_type": "TEXT",
            "text": text,
            "access_token": config.THREADS_ACCESS_TOKEN,
        },
        timeout=15
    )
    r.raise_for_status()
    creation_id = r.json()["id"]

    # Jeda sebentar sebelum publish (rekomendasi Meta)
    time.sleep(2)

    # Step 2: Publish
    r = requests.post(
        f"{base}/threads_publish",
        params={
            "creation_id": creation_id,
            "access_token": config.THREADS_ACCESS_TOKEN,
        },
        timeout=15
    )
    r.raise_for_status()
    thread_id = r.json()["id"]
    return thread_id


def post_all(text):
    """Post ke X dan Threads, return dict hasil."""
    results = {}

    try:
        url = post_to_x(text)
        results["x"] = f"✅ X posted: {url}"
    except Exception as e:
        results["x"] = f"❌ X gagal: {e}"

    try:
        thread_id = post_to_threads(text)
        results["threads"] = f"✅ Threads posted (id: {thread_id})"
    except Exception as e:
        results["threads"] = f"❌ Threads gagal: {e}"

    return results
