import os
import json
import time
import random
import asyncio
import requests
import subprocess
import edge_tts
import imageio_ffmpeg
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PIXABAY_API_KEY = os.environ["PIXABAY_API_KEY"]
ZERNIO_API_KEY = os.environ["ZERNIO_API_KEY"]
ZERNIO_ACC1_ID = os.environ["ZERNIO_ACC1_ID"]
ZERNIO_ACC2_ID = os.environ["ZERNIO_ACC2_ID"]

client = genai.Client(api_key=GEMINI_API_KEY)
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

NICHES = {
    "acc1": {
        "account_id": ZERNIO_ACC1_ID,
        "name": "Relationship & Psychology Drama",
        "voice": "en-US-AndrewNeural",
        "video_queries": ["satisfying slime", "soap cutting", "abstract colorful liquid", "sand art"],
        "hashtags": ["#storytime", "#redditstories", "#relationshipadvice", "#drama"],
        "prompt": (
            "Write a viral, high-retention 72-second Reddit-style relationship or psychology drama story "
            "for TikTok UK/USA Creator Rewards. Start immediately in sentence 1 with a shocking confession "
            "or discovery hook (NO intro, NO 'hey guys'). Build tension fast with twists and end on a "
            "gripping cliffhanger or thought-provoking question. Target length: 165 to 185 spoken words "
            "(strictly over 62 seconds when read aloud). Return ONLY valid JSON with keys: "
            "'title' (catchy 60-char caption) and 'script' (clean spoken narration only, no stage directions)."
        ),
    },
    "acc2": {
        "account_id": ZERNIO_ACC2_ID,
        "name": "ASMR & Experimental Destruction",
        "voice": "en-GB-RyanNeural",
        "video_queries": ["hydraulic press", "crushing glass", "slow motion explosion", "metal melting"],
        "hashtags": ["#satisfying", "#asmr", "#hydraulicpress", "#oddlysatisfying"],
        "prompt": (
            "Write a 68-second high-tension sensory commentary script for a satisfying destruction / hydraulic "
            "press TikTok video targeting UK/USA audiences. Start in the first 3 seconds with a bold outcome "
            "prediction question ('Will a 100-ton hydraulic press vaporize solid tungsten or shatter the steel plate?'). "
            "Describe the extreme pressure, sound, and suspense leading to the final payoff, and ask viewers to comment "
            "their guess. Target length: 155 to 175 spoken words (strictly over 62 seconds). Return ONLY valid JSON "
            "with keys: 'title' (catchy 60-char caption) and 'script' (clean spoken narration only)."
        ),
    },
}


def generate_script(niche_cfg):
    for model_name in ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.1-flash-lite"]:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=niche_cfg["prompt"],
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return json.loads(res.text)
        except Exception as e:
            print(f"{model_name} error: {e}")
            time.sleep(3)
    raise Exception("Failed to generate script from Gemini.")


def format_srt_time(seconds):
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


async def create_voice_and_subtitles(script_text, voice, audio_path, srt_path):
    communicate = edge_tts.Communicate(script_text, voice, rate="+4%")
    word_events = []
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start_s = chunk["offset"] / 10_000_000
                dur_s = chunk["duration"] / 10_000_000
                word_events.append((start_s, start_s + dur_s, chunk["text"]))

    srt_lines = []
    idx = 1
    for i in range(0, len(word_events), 3):
        group = word_events[i : i + 3]
        start_t = group[0][0]
        end_t = group[-1][1]
        phrase = " ".join(w[2] for w in group).upper()
        srt_lines.append(f"{idx}\n{format_srt_time(start_t)} --> {format_srt_time(end_t)}\n{phrase}\n")
        idx += 1

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))


def get_audio_duration(audio_path):
    cmd = [ffmpeg_exe, "-i", audio_path]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    for line in res.stderr.splitlines():
        if "Duration:" in line:
            t_str = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t_str.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 66.0


def fetch_pixabay_clips(queries, needed_duration):
    clip_urls = []
    for q in queries:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": PIXABAY_API_KEY, "q": q, "per_page": 15},
            timeout=20,
        )
        if r.status_code == 200:
            for hit in r.json().get("hits", []):
                vids = hit.get("videos", {})
                medium = vids.get("medium") or vids.get("small") or vids.get("large")
                if medium and medium.get("url"):
                    clip_urls.append(medium["url"])

    if not clip_urls:
        raise Exception("No video clips returned from Pixabay! Check your PIXABAY_API_KEY.")

    random.shuffle(clip_urls)
    os.makedirs("temp_clips", exist_ok=True)
    cut_files = []
    total_acc = 0.0
    idx = 0

    while total_acc < needed_duration + 2.0:
        url = clip_urls[idx % len(clip_urls)]
        raw_p = f"temp_clips/raw_{idx}.mp4"
        cut_p = f"temp_clips/cut_{idx}.mp4"
        try:
            with requests.get(url, stream=True, timeout=25) as resp:
                with open(raw_p, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        f.write(chunk)

            vf = (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,hflip,setpts=0.95*PTS,"
                "eq=contrast=1.06:saturation=1.12,fps=30"
            )
            cmd = [
                ffmpeg_exe, "-y", "-ss", "1", "-t", "2.6", "-i", raw_p,
                "-an", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", cut_p
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if os.path.exists(cut_p) and os.path.getsize(cut_p) > 10000:
                cut_files.append(cut_p)
                total_acc += 2.5
        except Exception as e:
            print(f"Clip {idx} skip: {e}")
        finally:
            if os.path.exists(raw_p):
                os.remove(raw_p)
        idx += 1

    return cut_files


def render_final_video(cut_files, audio_path, srt_path, final_out):
    list_file = "temp_clips/concat.txt"
    with open(list_file, "w") as f:
        for cf in cut_files:
            f.write(f"file '{os.path.abspath(cf)}'\n")

    merged_bg = "temp_clips/merged_bg.mp4"
    subprocess.run(
        [ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", merged_bg],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

    subtitle_style = (
        "FontName=Arial,FontSize=18,PrimaryColour=&H0000FFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=2,Alignment=10"
    )
    cmd = [
        ffmpeg_exe, "-y", "-i", merged_bg, "-i", audio_path,
        "-vf", f"subtitles={srt_path}:force_style='{subtitle_style}'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k", "-shortest", final_out
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def upload_to_zernio(video_path, account_id, caption_text):
    headers = {"Authorization": f"Bearer {ZERNIO_API_KEY}"}
    with open(video_path, "rb") as vf:
        media_res = requests.post(
            "https://zernio.com/api/v1/media",
            headers=headers,
            files={"file": ("tiktok_video.mp4", vf, "video/mp4")},
            timeout=120,
        )
    if media_res.status_code not in (200, 201):
        raise Exception(f"Zernio media upload error ({media_res.status_code}): {media_res.text}")

    media_url = media_res.json().get("url") or media_res.json().get("mediaUrl")

    payload = {
        "content": caption_text,
        "mediaItems": [{"type": "video", "url": media_url}],
        "platforms": [{"platform": "tiktok", "accountId": account_id}],
        "publishNow": True,
    }
    post_res = requests.post(
        "https://zernio.com/api/v1/posts",
        headers={**headers, "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if post_res.status_code not in (200, 201):
        raise Exception(f"Zernio post publish error ({post_res.status_code}): {post_res.text}")
    print("Successfully published to TikTok via Zernio:", post_res.json())


def run_for_account(niche_key):
    cfg = NICHES[niche_key]
    print(f"=== Running Autopilot for {cfg['name']} ===")
    data = generate_script(cfg)
    script_text = data["script"]
    tags = " ".join(cfg["hashtags"])
    caption = f"{data['title']} {tags}"

    audio_path = f"{niche_key}_voice.mp3"
    srt_path = f"{niche_key}_subs.srt"
    final_video = f"{niche_key}_final.mp4"

    asyncio.run(create_voice_and_subtitles(script_text, cfg["voice"], audio_path, srt_path))
    dur = get_audio_duration(audio_path)
    print(f"Generated voiceover duration: {dur:.1f}s")

    clips = fetch_pixabay_clips(cfg["video_queries"], dur)
    render_final_video(clips, audio_path, srt_path, final_video)
    upload_to_zernio(final_video, cfg["account_id"], caption)


if __name__ == "__main__":
    target = os.environ.get("TARGET_ACCOUNT", "acc1")
    run_for_account(target)
