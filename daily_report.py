import os
import re
import json
import requests
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

WHAPI_TOKEN = os.environ["WHAPI_TOKEN"]
WHATSAPP_PHONE = os.environ["WHATSAPP_PHONE"].strip().lstrip("+")
ACC1_USER = os.environ["TIKTOK_ACC1_USER"].strip().lstrip("@")
ACC2_USER = os.environ["TIKTOK_ACC2_USER"].strip().lstrip("@")
ZERNIO_API_KEY = os.environ.get("ZERNIO_API_KEY", "")

PKT_TZ = timezone(timedelta(hours=5))


def fetch_zernio_timestamps():
    """Gets exact PKT upload timestamps per account from Zernio as backup alignment."""
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
                        if uname in history and dt_pkt:
                            history[uname].append(dt_pkt)
    except Exception as e:
        print("Zernio timestamp warning:", e)

    for u in history:
        history[u].sort()
    return history


def extract_items_from_payload(obj, items_map):
    if isinstance(obj, dict):
        vid_id = obj.get("id")
        create_time = obj.get("createTime")
        stats = obj.get("stats")
        if vid_id and str(vid_id).isdigit() and create_time and isinstance(stats, dict) and "playCount" in stats:
            try:
                ts = int(create_time)
                if ts > 1600000000:
                    items_map[str(vid_id)] = {
                        "id": str(vid_id),
                        "ts": ts,
                        "views": int(stats.get("playCount", 0)),
                    }
            except Exception:
                pass
        for v in obj.values():
            extract_items_from_payload(v, items_map)
    elif isinstance(obj, list):
        for el in obj:
            extract_items_from_payload(el, items_map)


def scrape_profile_with_browser(username):
    """Uses headless Chromium to capture exact follower, like, video counts and individual post views."""
    url = f"https://www.tiktok.com/@{username}"
    result = {"followers": "0", "likes": "0", "videos": "0", "posts": []}
    items_map = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
                locale="en-GB",
            )
            page = context.new_page()

            def handle_response(response):
                if "api/post/item_list" in response.url or "api/user/detail" in response.url:
                    try:
                        data = response.json()
                        extract_items_from_payload(data, items_map)
                    except Exception:
                        pass

            page.on("response", handle_response)
            page.goto(url, wait_until="networkidle", timeout=35000)
            page.wait_for_timeout(3000)
            html = page.content()

            # Also parse embedded JSON if present
            for script_id in ("__UNIVERSAL_DATA_FOR_REHYDRATION__", "SIGI_STATE"):
                m = re.search(rf'<script[^>]*id="{script_id}"[^>]*>(.*?)</script>', html, re.DOTALL)
                if m:
                    try:
                        extract_items_from_payload(json.loads(m.group(1)), items_map)
                    except Exception:
                        pass

            # Fallback DOM extraction for visible video cards & view badges
            if not items_map:
                cards = page.query_selector_all('[data-e2e="user-post-item"]')
                for idx, card in enumerate(cards):
                    txt = card.inner_text().strip().splitlines()
                    view_str = txt[-1] if txt else "0"
                    items_map[f"dom_{idx}"] = {"id": f"dom_{idx}", "ts": idx, "views_text": view_str}

            followers = re.search(r'"followerCount"\s*:\s*(\d+)', html)
            hearts = re.search(r'"heartCount"\s*:\s*(\d+)', html)
            videos = re.search(r'"videoCount"\s*:\s*(\d+)', html)

            if followers:
                result["followers"] = f"{int(followers.group(1)):,}"
            if hearts:
                result["likes"] = f"{int(hearts.group(1)):,}"
            if videos:
                result["videos"] = f"{int(videos.group(1)):,}"

            browser.close()
    except Exception as e:
        print(f"Browser scrape warning for @{username}: {e}")

    # Sort oldest -> newest (Post 1 = first uploaded, Post 2 = second, etc.)
    sorted_items = sorted(items_map.values(), key=lambda x: x["ts"])
    result["posts"] = sorted_items
    return result


def format_account_section(label, username, tk_data, zernio_times):
    lines = [
        f"*{label} (@{username})*",
        f"Followers: *{tk_data['followers']}*  |  Likes: *{tk_data['likes']}*  |  Videos: *{tk_data['videos']}*",
        "",
    ]

    posts = tk_data.get("posts", [])
    if posts:
        # If DOM fallback was used (newest first on TikTok grid), reverse so Post 1 is oldest
        if "views_text" in posts[0]:
            posts = list(reversed(posts))

        for idx, p in enumerate(posts, start=1):
            if "views_text" in p:
                views_display = f"{p['views_text']} Views"
                dt_obj = zernio_times[idx - 1] if idx - 1 < len(zernio_times) else None
                time_display = dt_obj.strftime("%d %b, %I:%M %p PKT") if dt_obj else "Uploaded"
            else:
                views_display = f"{p['views']:,} Views"
                dt_obj = datetime.fromtimestamp(p["ts"], tz=PKT_TZ)
                time_display = dt_obj.strftime("%d %b, %I:%M %p PKT")

            lines.append(f"  *Post {idx}:* *{views_display}* ({time_display})")
    else:
        for idx, dt_obj in enumerate(zernio_times, start=1):
            lines.append(f"  *Post {idx}:* Syncing Views ({dt_obj.strftime('%d %b, %I:%M %p PKT')})")

    lines.append(f"Profile: https://www.tiktok.com/@{username}")
    return "\n".join(lines)


def send_whatsapp_report():
    now_pkt = datetime.now(PKT_TZ)
    date_str = now_pkt.strftime("%d %b %Y (%A)")
    time_str = now_pkt.strftime("%I:%M %p PKT")

    zernio_times = fetch_zernio_timestamps()
    acc1_tk = scrape_profile_with_browser(ACC1_USER)
    acc2_tk = scrape_profile_with_browser(ACC2_USER)

    sec1 = format_account_section("1. ACCOUNT 1", ACC1_USER, acc1_tk, zernio_times.get(ACC1_USER.lower(), []))
    sec2 = format_account_section("2. ACCOUNT 2", ACC2_USER, acc2_tk, zernio_times.get(ACC2_USER.lower(), []))

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
    print("Clean view-count WhatsApp report sent successfully!")


if __name__ == "__main__":
    send_whatsapp_report()
