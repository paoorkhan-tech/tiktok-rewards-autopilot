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


def extract_videos_from_json(obj, found_map):
    """Recursively finds TikTok video objects containing id, createTime, and stats.playCount."""
    if isinstance(obj, dict):
        vid_id = obj.get("id")
        create_time = obj.get("createTime")
        stats = obj.get("stats")
        if (
            vid_id
            and str(vid_id).isdigit()
            and create_time
            and isinstance(stats, dict)
            and "playCount" in stats
        ):
            try:
                ts = int(create_time)
                views = int(stats.get("playCount", 0))
                likes = int(stats.get("diggCount", 0))
                desc = str(obj.get("desc", "")).strip()
                if ts > 1600000000:
                    found_map[str(vid_id)] = {
                        "id": str(vid_id),
                        "create_time": ts,
                        "views": views,
                        "likes": likes,
                        "desc": desc,
                    }
            except Exception:
                pass
        for v in obj.values():
            extract_videos_from_json(v, found_map)
    elif isinstance(obj, list):
        for item in obj:
            extract_videos_from_json(item, found_map)


def fetch_public_tiktok_profile(username):
    url = f"https://www.tiktok.com/@{username}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-GB,en;q=0.9",
    }
    stats_out = {
        "followers": "0",
        "likes": "0",
        "videos": "0",
        "posts": [],
    }
    try:
        r = requests.get(url, headers=headers, timeout=25)
        html = r.text

        followers = re.search(r'"followerCount"\s*:\s*(\d+)', html)
        hearts = re.search(r'"heartCount"\s*:\s*(\d+)', html)
        videos = re.search(r'"videoCount"\s*:\s*(\d+)', html)

        if followers:
            stats_out["followers"] = f"{int(followers.group(1)):,}"
        if hearts:
            stats_out["likes"] = f"{int(hearts.group(1)):,}"
        if videos:
            stats_out["videos"] = f"{int(videos.group(1)):,}"

        found_videos = {}
        for script_id in ("__UNIVERSAL_DATA_FOR_REHYDRATION__", "SIGI_STATE"):
            m = re.search(
                rf'<script[^>]*id="{script_id}"[^>]*>(.*?)</script>',
                html,
                re.DOTALL,
            )
            if m:
                try:
                    parsed = json.loads(m.group(1))
                    extract_videos_from_json(parsed, found_videos)
                except Exception:
                    pass

        # Sort oldest -> newest so Post 1 is first uploaded, Post 2 is second, etc.
        sorted_posts = sorted(found_videos.values(), key=lambda x: x["create_time"])
        stats_out["posts"] = sorted_posts
    except Exception as e:
        print(f"Profile fetch warning for @{username}: {e}")

    return stats_out


def format_account_section(label, username, data):
    lines = [
        f"*{label} (@{username})*",
        f"Followers: *{data['followers']}*  |  Likes: *{data['likes']}*  |  Videos: *{data['videos']}*",
        "",
    ]
    posts = data.get("posts", [])
    if posts:
        lines.append("*Posts Performance (Oldest to Latest):*")
        for idx, p in enumerate(posts, start=1):
            dt_pkt = datetime.fromtimestamp(p["create_time"], tz=PKT_TZ)
            uploaded_str = dt_pkt.strftime("%d %b, %I:%M %p PKT")
            views_str = f"{p['views']:,}"
            # Short clean title preview (max 28 chars without hashtags)
            clean_title = re.sub(r"#\S+", "", p.get("desc", "")).strip()
            short_title = (clean_title[:28] + "...") if len(clean_title) > 28 else clean_title
            title_part = f" — _{short_title}_" if short_title else ""
            lines.append(
                f"  *Post {idx}:* *{views_str} Views* ({uploaded_str}){title_part}"
            )
    else:
        lines.append("  _No public post metrics parsed yet (check profile link below)_")

    lines.append(f"Link: https://www.tiktok.com/@{username}")
    return "\n".join(lines)


def send_whatsapp_report():
    now_pkt = datetime.now(PKT_TZ)
    date_str = now_pkt.strftime("%d %b %Y (%A)")
    time_str = now_pkt.strftime("%I:%M %p PKT")

    acc1_data = fetch_public_tiktok_profile(ACC1_USER)
    acc2_data = fetch_public_tiktok_profile(ACC2_USER)

    sec1 = format_account_section("1. ACCOUNT 1", ACC1_USER, acc1_data)
    sec2 = format_account_section("2. ACCOUNT 2", ACC2_USER, acc2_data)

    report_msg = (
        f"*TIKTOK UK/USA ANALYTICS REPORT*\n"
        f"Date: {date_str}\n"
        f"Report Time: {time_str}\n"
        f"====================================\n\n"
        f"{sec1}\n\n"
        f"------------------------------------\n\n"
        f"{sec2}\n\n"
        f"====================================\n"
        f"_Auto-Schedule: Active (UK/USA Peak Hours)_"
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
    print("Upgraded WhatsApp report sent successfully!")


if __name__ == "__main__":
    send_whatsapp_report()
