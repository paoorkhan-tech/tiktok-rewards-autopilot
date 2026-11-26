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


def fetch_zernio_post_history():
    """Fetches exact published posts and timestamps from Zernio API grouped by TikTok username."""
    history = {ACC1_USER.lower(): [], ACC2_USER.lower(): []}
    if not ZERNIO_API_KEY:
        return history
    try:
        r = requests.get(
            "https://zernio.com/api/v1/posts?limit=100",
            headers={"Authorization": f"Bearer {ZERNIO_API_KEY}"},
            timeout=25,
        )
        if r.status_code == 200:
            posts = r.json().get("posts", [])
            for p in posts:
                if p.get("status") not in ("published", "partial"):
                    continue
                content = re.sub(r"#\S+", "", p.get("content", "")).strip()
                pub_time_str = p.get("publishedAt") or p.get("scheduledFor") or p.get("createdAt")
                dt_pkt = None
                if pub_time_str:
                    try:
                        dt_utc = datetime.fromisoformat(pub_time_str.replace("Z", "+00:00"))
                        dt_pkt = dt_utc.astimezone(PKT_TZ)
                    except Exception:
                        pass

                for plat in p.get("platforms", []):
                    if plat.get("platform") == "tiktok" and plat.get("status") == "published":
                        acc_obj = plat.get("accountId", {})
                        uname = ""
                        if isinstance(acc_obj, dict):
                            uname = str(acc_obj.get("username", "")).lower().lstrip("@")
                        if uname in history:
                            history[uname].append({
                                "title": content,
                                "dt_pkt": dt_pkt,
                                "ts": dt_pkt.timestamp() if dt_pkt else 0,
                                "views": None,
                            })
    except Exception as e:
        print("Zernio history fetch warning:", e)

    for uname in history:
        history[uname].sort(key=lambda x: x["ts"])
    return history


def extract_videos_recursive(obj, found_list):
    if isinstance(obj, dict):
        vid_id = obj.get("id")
        create_time = obj.get("createTime")
        stats = obj.get("stats")
        if vid_id and str(vid_id).isdigit() and create_time and isinstance(stats, dict) and "playCount" in stats:
            try:
                ts = int(create_time)
                if ts > 1600000000:
                    found_list.append({
                        "id": str(vid_id),
                        "ts": ts,
                        "views": int(stats.get("playCount", 0)),
                        "desc": re.sub(r"#\S+", "", str(obj.get("desc", ""))).strip(),
                    })
            except Exception:
                pass
        for v in obj.values():
            extract_videos_recursive(v, found_list)
    elif isinstance(obj, list):
        for item in obj:
            extract_videos_recursive(item, found_list)


def fetch_tiktok_public_data(username):
    url = f"https://www.tiktok.com/@{username}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
        ),
        "Accept-Language": "en-GB,en;q=0.9",
    }
    data = {"followers": "0", "likes": "0", "videos": "0", "scraped_posts": []}
    try:
        r = requests.get(url, headers=headers, timeout=25)
        html = r.text

        followers = re.search(r'"followerCount"\s*:\s*(\d+)', html)
        hearts = re.search(r'"heartCount"\s*:\s*(\d+)', html)
        videos = re.search(r'"videoCount"\s*:\s*(\d+)', html)
        sec_uid_m = re.search(r'"secUid"\s*:\s*"([^"]+)"', html)

        if followers:
            data["followers"] = f"{int(followers.group(1)):,}"
        if hearts:
            data["likes"] = f"{int(hearts.group(1)):,}"
        if videos:
            data["videos"] = f"{int(videos.group(1)):,}"

        found = []
        for script_id in ("__UNIVERSAL_DATA_FOR_REHYDRATION__", "SIGI_STATE"):
            m = re.search(rf'<script[^>]*id="{script_id}"[^>]*>(.*?)</script>', html, re.DOTALL)
            if m:
                try:
                    extract_videos_recursive(json.loads(m.group(1)), found)
                except Exception:
                    pass

        # Fallback: Try public item_list endpoint if secUid found & HTML had no items
        if not found and sec_uid_m:
            try:
                api_url = (
                    f"https://www.tiktok.com/api/post/item_list/?aid=1988&count=30"
                    f"&secUid={sec_uid_m.group(1)}&cursor=0"
                )
                ar = requests.get(api_url, headers=headers, timeout=15)
                if ar.status_code == 200 and ar.text.strip():
                    extract_videos_recursive(ar.json(), found)
            except Exception:
                pass

        # Deduplicate & sort oldest -> newest
        unique_map = {item["id"]: item for item in found}
        data["scraped_posts"] = sorted(unique_map.values(), key=lambda x: x["ts"])
    except Exception as e:
        print(f"TikTok scrape warning for @{username}: {e}")

    return data


def format_account_section(label, username, tk_data, zernio_posts):
    lines = [
        f"*{label} (@{username})*",
        f"Followers: *{tk_data['followers']}*  |  Total Likes: *{tk_data['likes']}*  |  Videos: *{tk_data['videos']}*",
        "",
    ]

    scraped = tk_data.get("scraped_posts", [])

    # Merge Zernio exact timestamps with TikTok view counts
    merged_posts = []
    if scraped:
        for i, sp in enumerate(scraped):
            dt_pkt = datetime.fromtimestamp(sp["ts"], tz=PKT_TZ)
            merged_posts.append({
                "uploaded": dt_pkt.strftime("%d %b, %I:%M %p PKT"),
                "views": f"{sp['views']:,} Views",
                "title": sp["desc"],
            })
    elif zernio_posts:
        for zp in zernio_posts:
            up_str = zp["dt_pkt"].strftime("%d %b, %I:%M %p PKT") if zp["dt_pkt"] else "Uploaded"
            merged_posts.append({
                "uploaded": up_str,
                "views": "Live on FYP",
                "title": zp["title"],
            })

    if merged_posts:
        lines.append("*Posts Breakdown (Post 1 to Latest):*")
        for idx, post in enumerate(merged_posts, start=1):
            short_t = (post["title"][:26] + "...") if len(post["title"]) > 26 else post["title"]
            t_label = f" — _{short_t}_" if short_t else ""
            lines.append(f"  *Post {idx}:* *{post['views']}* | {post['uploaded']}{t_label}")
    else:
        lines.append("  _Posts syncing — check live profile below_")

    lines.append(f"Profile: https://www.tiktok.com/@{username}")
    return "\n".join(lines)


def send_whatsapp_report():
    now_pkt = datetime.now(PKT_TZ)
    date_str = now_pkt.strftime("%d %b %Y (%A)")
    time_str = now_pkt.strftime("%I:%M %p PKT")

    zernio_history = fetch_zernio_post_history()
    acc1_tk = fetch_tiktok_public_data(ACC1_USER)
    acc2_tk = fetch_tiktok_public_data(ACC2_USER)

    sec1 = format_account_section("1. ACCOUNT 1", ACC1_USER, acc1_tk, zernio_history.get(ACC1_USER.lower(), []))
    sec2 = format_account_section("2. ACCOUNT 2", ACC2_USER, acc2_tk, zernio_history.get(ACC2_USER.lower(), []))

    report_msg = (
        f"*TIKTOK UK/USA ANALYTICS REPORT*\n"
        f"Date: {date_str}\n"
        f"Report Time: {time_str}\n"
        f"====================================\n\n"
        f"{sec1}\n\n"
        f"------------------------------------\n\n"
        f"{sec2}\n\n"
        f"====================================\n"
        f"_Next Auto-Report: 6:00 AM PKT_"
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
    print("Final hybrid WhatsApp report sent successfully!")


if __name__ == "__main__":
    send_whatsapp_report()
