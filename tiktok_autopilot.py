import os
import re
import json
import time
import random
import asyncio
import urllib.parse
import requests
import subprocess
import edge_tts
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
PIXABAY_API_KEY = os.environ["PIXABAY_API_KEY"]
ZERNIO_API_KEY = os.environ["ZERNIO_API_KEY"]
ZERNIO_ACC1_ID = os.environ["ZERNIO_ACC1_ID"]
ZERNIO_ACC2_ID = os.environ["ZERNIO_ACC2_ID"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]

client = genai.Client(api_key=GEMINI_API_KEY)
ffmpeg_exe = "ffmpeg"
STATE_FILE = "story_state.json"

NICHES = {
    "acc1": {
        "account_id": ZERNIO_ACC1_ID,
        "name": "Relationship & Psychology Drama (30s 2-Part Curiosity Series)",
        "mode": "story_2part_30s",
        "voices": ["en-US-AndrewNeural", "en-US-GuyNeural", "en-US-ChristopherNeural", "en-GB-RyanNeural"],
        "hashtags": ["#storytime", "#redditstories", "#psychology", "#plottwist"],
    },
    "acc2": {
        "account_id": ZERNIO_ACC2_ID,
        "name": "ASMR & Hydraulic Press Destruction (30s Exact Real Match)",
        "mode": "real_matched_30s",
        "voices": ["en-GB-RyanNeural", "en-US-AndrewNeural", "en-US-GuyNeural", "en-GB-ThomasNeural"],
        "primary_queries": ["hydraulic press", "crushing object", "metal press", "glass crushing"],
        "hashtags": ["#satisfying", "#asmr", "#hydraulicpress", "#oddlysatisfying"],
    },
}


def load_story_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"pending_part2": None}


def save_story_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def call_gemini_json(prompt_text):
    for model_name in ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash"]:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt_text,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return json.loads(res.text)
        except Exception as e:
            print(f"{model_name} error: {e}")
            time.sleep(2)
    raise Exception("Failed to generate script from Gemini.")


def generate_acc1_2part_script():
    state = load_story_state()
    pending = state.get("pending_part2")

    if pending:
        print("=== Generating PART 2 of ongoing cliffhanger story ===")
        prompt_text = (
            f"You are writing PART 2 (the thrilling conclusion) of a viral 2-part TikTok story.\n"
            f"Story Premise: {pending['premise']}\n"
            f"Part 1 ended on this exact cliffhanger: {pending['cliffhanger']}\n\n"
            "Write a high-retention ~30-second PART 2 script for UK/USA audiences. "
            "Start immediately with 'Part 2:' and reveal the shocking twist that resolves the cliffhanger. "
            "Make both sides slightly relatable/debatable and end with a strong polarizing question that sparks "
            "comments and profile follows ('Who was actually wrong here? Comment your verdict—and follow for tonight's new story!'). "
            "IMPORTANT: Write strictly between 95 and 112 spoken words so the voiceover is ~30 seconds. "
            "Return ONLY valid JSON with keys: "
            "'title' (catchy Part 2 caption max 60 chars), "
            "'script' (clean spoken narration only), "
            "'ai_intro_scenes' (array of 3 photorealistic vertical 9:16 image prompts depicting the shocking Part 2 reveal in the first 15s), and "
            "'pixabay_queries' (array of 3 mood-matched stock video search terms for the second half)."
        )
        data = call_gemini_json(prompt_text)
        state["pending_part2"] = None
        save_story_state(state)
        return data, "Part 2"
    else:
        print("=== Generating PART 1 of new 2-part curiosity story ===")
        prompt_text = (
            "Write PART 1 of a viral, high-retention 2-part Reddit-style relationship or psychology drama story "
            "for UK/USA TikTok audiences. Start immediately in sentence 1 with a jaw-dropping confession or discovery "
            "hook (NO intro, NO 'hey guys'). Build unbearable curiosity in 25 seconds, then STOP right at the peak "
            "climax before the secret is revealed, ending with: 'What was inside changed everything—Part 2 drops next, "
            "follow right now so you don't miss the ending!' "
            "IMPORTANT: Write strictly between 95 and 112 spoken words so the voiceover is ~30 seconds. "
            "Return ONLY valid JSON with keys: "
            "'title' (catchy Part 1 caption max 60 chars), "
            "'script' (clean spoken narration only), "
            "'story_premise' (2-sentence summary of the full secret/twist so Part 2 can continue seamlessly), "
            "'cliffhanger_line' (the exact ending cliffhanger sentence), "
            "'ai_intro_scenes' (array of 3 photorealistic vertical 9:16 image prompts depicting the opening hook in the first 15s), and "
            "'pixabay_queries' (array of 3 mood-matched stock video search terms for the second half)."
        )
        data = call_gemini_json(prompt_text)
        state["pending_part2"] = {
            "premise": data.get("story_premise", data["script"]),
            "cliffhanger": data.get("cliffhanger_line", data["script"][-140:]),
        }
        save_story_state(state)
        return data, "Part 1"


def generate_acc2_script(matched_tags):
    prompt_text = (
        f"We have authentic, real hydraulic press / crushing video footage showing: '{matched_tags}'. "
        "Write a high-retention 30-second standalone sensory commentary script for UK/USA TikTok viewers "
        "that matches this EXACT real footage from second 1 to second 30. "
        "Start in the first 3 seconds with a bold 99% vs 1% prediction hook ('99% of people think this object "
        "will survive 150 tons—watch what happens at second 25!'). Describe the exact weight, density, and extreme "
        "pressure building up on screen so every word matches the real footage. End with a viewer challenge: "
        "'Comment the toughest object we should crush next—most liked comment gets tested tomorrow, follow to see!' "
        "IMPORTANT: Write strictly between 95 and 112 spoken words so the voiceover is ~30 seconds. "
        "Return ONLY valid JSON with keys: 'title' (catchy 60-char caption) and 'script' (clean spoken narration only)."
    )
    return call_gemini_json(prompt_text)


def format_srt_time(seconds):
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


async def create_voice_and_subtitles(script_text, voices, audio_path, srt_path):
    clean_text = re.sub(r"[^\w\s.,!?'\"-]", " ", script_text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    word_events = []
    success = False

    for voice in voices:
        for attempt in range(2):
            try:
                word_events = []
                communicate = edge_tts.Communicate(clean_text, voice, rate="+4%", boundary="WordBoundary")
                with open(audio_path, "wb") as f:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])
                        elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                            start_s = chunk["offset"] / 10_000_000
                            dur_s = chunk["duration"] / 10_000_000
                            word_events.append((start_s, start_s + dur_s, chunk["text"]))
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 4000:
                    print(f"Voiceover generated using {voice}")
                    success = True
                    break
            except Exception as e:
                print(f"TTS {voice} attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2)
        if success:
            break

    if not success:
        raise Exception("All Edge TTS voices failed to return audio.")

    srt_lines = []
    idx = 1
    if word_events:
        for i in range(0, len(word_events), 3):
            group = word_events[i : i + 3]
            start_t = group[0][0]
            end_t = group[-1][1]
            phrase = " ".join(w[2] for w in group).upper()
            srt_lines.append(f"{idx}\n{format_srt_time(start_t)} --> {format_srt_time(end_t)}\n{phrase}\n")
            idx += 1
    else:
        words = clean_text.split()
        step = 0.32
        for i in range(0, len(words), 3):
            start_t = (i / 3) * (step * 3)
            end_t = start_t + (step * 3)
            phrase = " ".join(words[i : i + 3]).upper()
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
    return 30.0


def generate_ai_intro_clips(ai_scenes, count=3):
    os.makedirs("temp_clips", exist_ok=True)
    ai_cut_files = []
    for i, scene_prompt in enumerate(ai_scenes[:count]):
        img_p = f"temp_clips/ai_story_{i}.jpg"
        vid_p = f"temp_clips/ai_story_{i}.mp4"
        full_prompt = (
            f"{scene_prompt}, cinematic dramatic lighting, photorealistic, 8k, emotional storytelling, vertical 9:16"
        )
        encoded = urllib.parse.quote(full_prompt)
        seed = random.randint(1000, 999999)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=720&height=1280&nologo=true&seed={seed}"
        try:
            r = requests.get(url, timeout=45)
            if r.status_code == 200 and len(r.content) > 5000:
                with open(img_p, "wb") as f:
                    f.write(r.content)
                vf = (
                    "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                    "zoompan=z='min(zoom+0.0012,1.15)':d=150:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920,"
                    "eq=contrast=1.06:saturation=1.12,fps=30"
                )
                cmd = [
                    ffmpeg_exe, "-y", "-loop", "1", "-i", img_p,
                    "-t", "5", "-an", "-vf", vf,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", vid_p
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.exists(vid_p) and os.path.getsize(vid_p) > 10000:
                    ai_cut_files.append(vid_p)
                    print(f"Generated AI intro scene {i + 1}/{count} (5.0s)")
        except Exception as e:
            print(f"AI intro scene {i + 1} skipped: {e}")
        finally:
            if os.path.exists(img_p):
                os.remove(img_p)
    return ai_cut_files


def search_pixabay_hits(queries):
    hits_list = []
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
                    hits_list.append({
                        "url": medium["url"],
                        "tags": hit.get("tags", q),
                        "duration": hit.get("duration", 10),
                    })
    if not hits_list:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": PIXABAY_API_KEY, "q": "satisfying abstract", "per_page": 15},
            timeout=20,
        )
        for hit in r.json().get("hits", []):
            vids = hit.get("videos", {})
            medium = vids.get("medium") or vids.get("small")
            if medium and medium.get("url"):
                hits_list.append({"url": medium["url"], "tags": hit.get("tags", "satisfying"), "duration": 10})
    return hits_list


def build_micro_cuts(clip_urls, needed_duration, prefix="cut", clip_len=2.6):
    os.makedirs("temp_clips", exist_ok=True)
    cut_files = []
    total_acc = 0.0
    idx = 0

    while total_acc < needed_duration:
        url = clip_urls[idx % len(clip_urls)]
        raw_p = f"temp_clips/raw_{prefix}_{idx}.mp4"
        cut_p = f"temp_clips/{prefix}_{idx}.mp4"
        try:
            with requests.get(url, stream=True, timeout=25) as resp:
                with open(raw_p, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        f.write(chunk)

            ss_offset = (idx // max(1, len(clip_urls))) * 2
            vf = (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,hflip,setpts=0.95*PTS,"
                "eq=contrast=1.06:saturation=1.12,fps=30"
            )
            cmd = [
                ffmpeg_exe, "-y", "-ss", str(ss_offset), "-t", str(clip_len), "-i", raw_p,
                "-an", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", cut_p
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if os.path.exists(cut_p) and os.path.getsize(cut_p) > 10000:
                cut_files.append(cut_p)
                total_acc += (clip_len - 0.1)
        except Exception as e:
            print(f"Clip {prefix}_{idx} skip: {e}")
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
        "FontName=DejaVu Sans,FontSize=19,PrimaryColour=&H0000FFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=2,Alignment=10"
    )
    cmd = [
        ffmpeg_exe, "-y", "-i", merged_bg, "-i", audio_path,
        "-vf", f"subtitles={srt_path}:force_style='{subtitle_style}'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-shortest", final_out
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise Exception(f"FFmpeg render error: {res.stderr[-800:]}")


def host_video_on_github_release(video_path):
    gh_headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    tag = "media-staging"
    rel_url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/tags/{tag}"
    rel_res = requests.get(rel_url, headers=gh_headers, timeout=30)

    if rel_res.status_code == 200:
        release = rel_res.json()
        for old_asset in release.get("assets", [])[:-4]:
            requests.delete(
                f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/assets/{old_asset['id']}",
                headers=gh_headers,
                timeout=15,
            )
    else:
        create_res = requests.post(
            f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases",
            headers=gh_headers,
            json={"tag_name": tag, "name": "Temporary Media Staging", "draft": False, "prerelease": True},
            timeout=30,
        )
        create_res.raise_for_status()
        release = create_res.json()

    upload_url = release["upload_url"].split("{")[0]
    asset_name = f"tiktok_{int(time.time())}.mp4"

    with open(video_path, "rb") as vf:
        up_res = requests.post(
            f"{upload_url}?name={asset_name}",
            headers={**gh_headers, "Content-Type": "video/mp4"},
            data=vf,
            timeout=120,
        )
    up_res.raise_for_status()
    download_url = up_res.json()["browser_download_url"]
    print("Hosted direct GitHub Release MP4 URL:", download_url)
    return download_url


def upload_to_zernio(video_path, account_id, caption_text):
    media_url = host_video_on_github_release(video_path)
    headers = {
        "Authorization": f"Bearer {ZERNIO_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "content": caption_text,
        "mediaItems": [{"type": "video", "url": media_url}],
        "platforms": [
            {
                "platform": "tiktok",
                "accountId": account_id,
                "platformSpecificData": {
                    "privacyLevel": "PUBLIC_TO_EVERYONE",
                    "allowComment": True,
                    "allowDuet": True,
                    "allowStitch": True,
                },
            }
        ],
        "publishNow": True,
    }
    post_res = requests.post(
        "https://zernio.com/api/v1/posts",
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp_json = post_res.json()
    platforms_info = resp_json.get("post", {}).get("platforms", [])
    if post_res.status_code not in (200, 201) or resp_json.get("post", {}).get("status") == "failed":
        raise Exception(f"Zernio TikTok publish failed ({post_res.status_code}): {json.dumps(platforms_info)}")
    print("Successfully published to TikTok via Zernio:", json.dumps(platforms_info))


def run_for_account(niche_key):
    cfg = NICHES[niche_key]
    print(f"=== Running Autopilot for {cfg['name']} ===")

    audio_path = f"{niche_key}_voice.mp3"
    srt_path = f"{niche_key}_subs.srt"
    final_video = f"{niche_key}_final.mp4"

    if cfg.get("mode") == "real_matched_30s":
        # Account 2: 30s standalone video with 100% real matched hydraulic press footage
        primary_hits = search_pixabay_hits(cfg["primary_queries"])
        hero_hit = random.choice(primary_hits)
        matched_tags = hero_hit["tags"]
        print(f"Selected Real Hydraulic Press Footage Tags: '{matched_tags}'")

        data = generate_acc2_script(matched_tags)
        script_text = data["script"]
        tags = " ".join(cfg["hashtags"])
        caption = f"{data['title']} {tags}"

        asyncio.run(create_voice_and_subtitles(script_text, cfg["voices"], audio_path, srt_path))
        dur = get_audio_duration(audio_path)
        print(f"Generated voiceover duration: {dur:.1f}s")

        hero_urls = [hero_hit["url"]] + [
            h["url"] for h in primary_hits if h["url"] != hero_hit["url"]
        ][:3]
        all_clips = build_micro_cuts(hero_urls, needed_duration=dur + 2.0, prefix="real30", clip_len=3.0)
    else:
        # Account 1: 30s 2-Part Curiosity Story (15s AI story intro + 15s mood-matched B-roll)
        data, part_label = generate_acc1_2part_script()
        script_text = data["script"]
        tags = " ".join(cfg["hashtags"])
        caption = f"[{part_label}] {data['title']} {tags}"

        asyncio.run(create_voice_and_subtitles(script_text, cfg["voices"], audio_path, srt_path))
        dur = get_audio_duration(audio_path)
        print(f"Generated {part_label} voiceover duration: {dur:.1f}s")

        ai_scenes = data.get("ai_intro_scenes") or [
            "Shocked person staring at a glowing smartphone screen in a dark bedroom at midnight",
            "Close up of a hidden secret envelope found inside an old wooden drawer, dramatic lighting",
            "Two silhouettes standing apart in a rainy city street at night, tense emotional atmosphere",
        ]
        ai_intro_clips = generate_ai_intro_clips(ai_scenes, count=3)
        ai_seconds = len(ai_intro_clips) * 5.0

        matched_queries = data.get("pixabay_queries") or ["rain on window night", "city night drive", "clock ticking"]
        print(f"Mood-matched B-Roll queries: {matched_queries}")
        broll_hits = search_pixabay_hits(matched_queries)
        broll_urls = [h["url"] for h in broll_hits]
        random.shuffle(broll_urls)

        remaining_dur = max(16.0, dur - ai_seconds + 2.0)
        matched_broll_clips = build_micro_cuts(broll_urls, needed_duration=remaining_dur, prefix="storybroll", clip_len=2.6)
        all_clips = ai_intro_clips + matched_broll_clips

    render_final_video(all_clips, audio_path, srt_path, final_video)
    upload_to_zernio(final_video, cfg["account_id"], caption)


if __name__ == "__main__":
    target = os.environ.get("TARGET_ACCOUNT", "acc1")
    run_for_account(target)
