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

PKT_TZ = timezone(timedelta(hours=5))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}


def fetch_single_video_views(username, post_id, post_url=""):
    """Fetches exact playCount directly from the public TikTok video page."""
    target_urls = []
    if post_url and "tiktok.com" in post_url:
        target_urls.append(post_url)
    if post_id and str(post_id).isdigit():
        target_urls.append(f"https://www.tiktok.com/@{username}/video/{post_id}")

    for url in target_urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            html = r.text
            # Match playCount inside the video's stats JSON block
            m = re.search(r'"stats"\s*:\s*\{[^}]*"playCount"\s*:\s*(\d+)', html)
            if m:
                return int(m.group(1))
            m2 = re.search(r'"playCount"\s*:\s*(\d+)', html)
            if m2:
                return int(m2.group(1))
        except Exception as e:
            print(f"Video views fetch warning ({url}): {e}")
    return None


def fetch_zernio_posts_with_views():
    """Gets all published posts per account from Zernio, then fetches live views for each post."""
    accounts_posts = {ACC1_USER.lower(): [], ACC2_USER.lower(): []}
    if not ZERNIO_API_KEY:
        return accounts_posts

    try:
        r = requests.get(
            "https://zernio.com/api/v1/posts?limit=100",
            headers={"Authorization": f"Bearer {ZERNIO_API_KEY}"},
            timeout=25,
        )
        if r.status_code == 200:
            for p in r.json().get("posts", []):
                if p.get("status") not in ("published", "partial"):
                    continue
                pub_str = p.get("publishedAt") or p.get("scheduledFor") or p.get("createdAt")
                dt_pkt = None
                if pub_str:
                    try:
                        dt_pkt = datetime.fromisoformat(pub_str.replace("Z", "+00:00")).astimezone(PKT_TZ)
                    except Exception:
                        pass

                for plat in p.get("platforms", []):
                    if plat.get("platform") == "tiktok" and plat.get("status") == "published":
                        acc_obj = plat.get("accountId", {})
                        uname = acc_obj.get("username", "").lower().lstrip("@") if isinstance(acc_obj, dict) else ""
                        if uname in accounts_posts:
                            post_id = str(plat.get("platformPostId") or "").strip()
                            post_url = str(plat.get("platformPostUrl") or "").strip()
                            views = fetch_single_video_views(uname, post_id, post_url)
                            accounts_posts[uname].append({
                                "ts": dt_pkt.timestamp() if dt_pkt else 0,
                                "dt_pkt": dt_pkt,
                                "views": views,
                            })
    except Exception as e:
        print("Zernio posts fetch warning:", e)

    for u in accounts_posts:
        accounts_posts[u].sort(key=lambda x: x["ts"])
    return accounts_posts


def fetch_profile_totals(username):
    url = f"https://www.tiktok.com/@{username}"
    totals = {"followers": "0", "likes": "0", "videos": "0"}
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        html = r.text
        f_m = re.search(r'"followerCount"\s*:\s*(\d+)', html)
        h_m = re.search(r'"heartCount"\s*:\s*(\d+)', html)
        v_m = re.search(r'"videoCount"\s*:\s*(\d+)', html)
        if f_m:
            totals["followers"] = f"{int(f_m.group(1)):,}"
        if h_m:
            totals["likes"] = f"{int(h_m.group(1)):,}"
        if v_m:
            totals["videos"] = f"{int(v_m.group(1)):,}"
    except Exception as e:
        print(f"Profile totals warning for @{username}: {e}")
    return totals


def format_account_section(label, username, totals, posts_list):
    lines = [
        f"*{label} (@{username})*",
        f"Followers: *{totals['followers']}*  |  Likes: *{totals['likes']}*  |  Videos: *{totals['videos']}*",
        "",
    ]

    if posts_list:
        for idx, item in enumerate(posts_list, start=1):
            time_str = item["dt_pkt"].strftime("%d %b, %I:%M %p PKT") if item["dt_pkt"] else "Uploaded"
            if item["views"] is not None:
                views_str = f"*{item['views']:,} Views*"
            else:
                views_str = "*Processing Views*"
            lines.append(f"  *Post {idx}:* {views_str} ({time_str})")
    else:
        lines.append("  _No posts recorded yet_")

    lines.append(f"Profile: https://www.tiktok.com/@{username}")
    return "\n".join(lines)


def send_whatsapp_report():
    now_pkt = datetime.now(PKT_TZ)
    date_str = now_pkt.strftime("%d %b %Y (%A)")
    time_str = now_pkt.strftime("%I:%M %p PKT")

    all_posts = fetch_zernio_posts_with_views()
    acc1_totals = fetch_profile_totals(ACC1_USER)
    acc2_totals = fetch_profile_totals(ACC2_USER)

    sec1 = format_account_section("1. ACCOUNT 1", ACC1_USER, acc1_totals, all_posts.get(ACC1_USER.lower(), []))
    sec2 = format_account_section("2. ACCOUNT 2", ACC2_USER, acc2_totals, all_posts.get(ACC2_USER.lower(), []))

    report_msg = (
        f"*TIKTOK UK/USA ANALYTICS REPORT*\n"
        f"Date: {date_str}\n"
        f"Time: {time_str}\n"
        f"====================================\n\n"
        f"{sec1}\n\n"
        f"------------------------------------\n\n"
        f"{sec2}\n\n"
        f"====================================\n"
        f"_Auto-Schedule Active (Next Report: 6:00 AM PKT)_"
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
    print("Exact post-level WhatsApp report sent successfully!")


if __name__ == "__main__":
    send_whatsapp_report()
