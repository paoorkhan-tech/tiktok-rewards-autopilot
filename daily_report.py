import os
import re
import json
import requests
from datetime import datetime, timezone, timedelta

WHAPI_TOKEN = os.environ["WHAPI_TOKEN"]
WHATSAPP_PHONE = os.environ["WHATSAPP_PHONE"].strip().lstrip("+")
ACC1_USER = os.environ["TIKTOK_ACC1_USER"].strip().lstrip("@")
ACC2_USER = os.environ["TIKTOK_ACC2_USER"].strip().lstrip("@")
ZERNIO_API_KEY = os.environ.get("ZERNIO_API_KEY", "")


def fetch_public_tiktok_stats(username):
    url = f"https://www.tiktok.com/@{username}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-GB,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=25)
        html = r.text
        followers = re.search(r'"followerCount"\s*:\s*(\d+)', html)
        hearts = re.search(r'"heartCount"\s*:\s*(\d+)', html)
        videos = re.search(r'"videoCount"\s*:\s*(\d+)', html)
        if followers:
            return {
                "followers": f"{int(followers.group(1)):,}",
                "likes": f"{int(hearts.group(1)):,}" if hearts else "0",
                "videos": f"{int(videos.group(1)):,}" if videos else "0",
            }
    except Exception as e:
        print(f"Stats fetch warning for @{username}: {e}")
    return {"followers": "Check Link", "likes": "Check Link", "videos": "Active"}


def fetch_recent_zernio_posts():
    if not ZERNIO_API_KEY:
        return "N/A"
    try:
        r = requests.get(
            "https://zernio.com/api/v1/posts?limit=15",
            headers={"Authorization": f"Bearer {ZERNIO_API_KEY}"},
            timeout=20,
        )
        if r.status_code == 200:
            posts = r.json().get("posts", [])
            published = sum(1 for p in posts if p.get("status") == "published")
            return f"{published} / {len(posts)} Recent Posts Published"
    except Exception as e:
        print("Zernio status check warning:", e)
    return "Active"


def send_whatsapp_report():
    pkt_tz = timezone(timedelta(hours=5))
    now_pkt = datetime.now(pkt_tz)
    date_str = now_pkt.strftime("%d %b %Y (%A)")
    time_str = now_pkt.strftime("%I:%M %p PKT")

    acc1 = fetch_public_tiktok_stats(ACC1_USER)
    acc2 = fetch_public_tiktok_stats(ACC2_USER)
    zernio_summary = fetch_recent_zernio_posts()

    report_msg = (
        f"*TIKTOK UK/USA AUTOPILOT DAILY REPORT*\n"
        f"Date: {date_str}\n"
        f"Time: {time_str}\n"
        f"----------------------------------\n\n"
        f"*1. Account 1 (@{ACC1_USER})*\n"
        f"- Followers: {acc1['followers']}\n"
        f"- Total Likes: {acc1['likes']}\n"
        f"- Total Videos: {acc1['videos']}\n"
        f"- Profile: https://www.tiktok.com/@{ACC1_USER}\n\n"
        f"*2. Account 2 (@{ACC2_USER})*\n"
        f"- Followers: {acc2['followers']}\n"
        f"- Total Likes: {acc2['likes']}\n"
        f"- Total Videos: {acc2['videos']}\n"
        f"- Profile: https://www.tiktok.com/@{ACC2_USER}\n\n"
        f"*System Health:* {zernio_summary}\n"
        f"_Next Auto-Cycle: 6:00 PM PKT (UK/USA Peak)_"
    )

    chat_id = f"{WHATSAPP_PHONE}@s.whatsapp.net"
    res = requests.post(
        "https://gate.whapi.cloud/messages/text",
        headers={
            "Authorization": f"Bearer {WHAPI_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"to": chat_id, "body": report_msg},
        timeout=30,
    )
    print("Whapi response:", res.status_code, res.text)
    if res.status_code not in (200, 201):
        raise Exception(f"WhatsApp report send failed ({res.status_code}): {res.text}")
    print("Daily WhatsApp report sent successfully!")


if __name__ == "__main__":
    send_whatsapp_report()
