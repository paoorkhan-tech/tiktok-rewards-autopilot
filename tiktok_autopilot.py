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
        "voices": ["en-US-AndrewMultilingualNeural", "en-US-AndrewNeural", "en-US-ChristopherNeural", "en-GB-RyanNeural"],
        "tts_rate": "+4%",
        "tts_pitch": "+0Hz",
        "hashtags": ["#storytime", "#redditstories", "#psychology", "#plottwist"],
    },
    "acc2": {
        "account_id": ZERNIO_ACC2_ID,
        "name": "English Deep Life Reality & Regret (22yo Adam-Style Fast Realistic Voice + Guaranteed BGM + 2s Cuts)",
        "mode": "deep_life_english_30s",
        # Natural, realistic 22-23yo male voices (clean normal pitch, fast engaging delivery)
        "voices": ["en-US-AndrewNeural", "en-US-BrianNeural", "en-CA-LiamNeural", "en-US-GuyNeural"],
        "tts_rate": "+9%",
        "tts_pitch": "+1Hz",
        "hashtags": ["#lifereality", "#deepthoughts", "#regret", "#mindset", "#motivation", "#realitycheck"],
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


def generate_acc2_deep_life_english():
    topics = [
        "The silent sacrifice of aging parents while we stay too busy staring at our phones",
        "Ignoring the messages of the one person who truly loves you until their number goes silent forever",
        "Chasing money and fake validation while slowly losing the people who actually care",
        "A father hiding his own struggles and worn-out shoes just so his kids never feel less than anyone",
        "The brutal truth of life: people only realize your value when you are no longer there",
        "Thinking you still have plenty of time to say 'I love you'—until life proves you wrong",
    ]
    chosen_topic = random.choice(topics)
    prompt_text = (
        f"You are a raw, honest, realistic 23-year-old storyteller talking directly to viewers on TikTok.\n"
        f"Topic theme: {chosen_topic}\n\n"
        "Write a high-retention, deeply emotional 30-second STANDALONE life reality & regret story in natural conversational English.\n"
        "Break the narration into 8 to 9 punchy, flowing sentences (total 92 to 105 spoken words) so the voice sounds "
        "100% human, fast-paced, and real—never robotic or overly poetic.\n"
        "CRITICAL STRUCTURE (NO Part 1 / Part 2 — complete standalone 30s video):\n"
        "- Lines 1-2 (0-6s HEAVY STOPPING HOOK): Open immediately with an ultra-strong, uncomfortable truth that hits the "
        "viewer in the chest in the first 3 seconds so they physically cannot scroll past.\n"
        "- Lines 3-6 (6-22s): Raw, relatable storytelling about family, quiet sacrifice, and the regret of taking people for granted.\n"
        "- Lines 7-9 (22-30s): A gut-punch final realization + a short, genuine prompt asking viewers to comment or text someone they love.\n\n"
        "Return ONLY valid JSON with these exact keys:\n"
        "- 'title': Catchy, emotional TikTok caption (max 55 chars)\n"
        "- 'lines': Array of 8 to 9 objects, where each object has:\n"
        "    - 'text': Clean, natural spoken English sentence (no emojis, no hashtags)\n"
        "    - 'pause_after': Float seconds of tiny natural breath pause after this sentence (strictly between 0.08 and 0.16)\n"
        "- 'hook_queries': Array of 2 English Pixabay video search queries matching lines 1-2 (0-10s) (e.g. ['sad man rain window', 'looking at phone dark'])\n"
        "- 'mid_queries': Array of 2 English Pixabay video search queries matching lines 3-6 (10-20s) (e.g. ['father holding child', 'elderly man working'])\n"
        "- 'end_queries': Array of 2 English Pixabay video search queries matching lines 7-9 (20-30s) (e.g. ['lonely sunset walking', 'crying emotional person'])"
    )
    return call_gemini_json(prompt_text)


def format_srt_time(seconds):
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def get_audio_duration(audio_path):
    cmd = [ffmpeg_exe, "-i", audio_path]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    for line in res.stderr.splitlines():
        if "Duration:" in line:
            t_str = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t_str.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 30.0


async def synthesize_single_line(text, voices, out_mp3, rate, pitch):
    clean_tts = re.sub(r"[^\w\s.,!?'\"-]", " ", text)
    clean_tts = re.sub(r"\s+", " ", clean_tts).strip()
    for voice in voices:
        for attempt in range(2):
            try:
                communicate = edge_tts.Communicate(clean_tts, voice, rate=rate, pitch=pitch)
                await communicate.save(out_mp3)
                if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 1500:
                    return voice
            except Exception as e:
                print(f"Line TTS ({voice}) attempt {attempt + 1} error: {e}")
                await asyncio.sleep(1.5)
    raise Exception(f"Failed to synthesize line: {clean_tts[:40]}")


async def create_fast_realistic_voice_and_subs(lines_data, voices, audio_path, srt_path, rate="+9%", pitch="+1Hz"):
    """Generates fast, natural 22-23yo Adam-style English narration with micro breath pauses and tight subtitles."""
    os.makedirs("temp_clips/tts_parts", exist_ok=True)
    concat_items = []
    srt_lines = []
    current_time = 0.0
    sub_idx = 1

    for i, item in enumerate(lines_data):
        spoken_line = (item.get("text") or "").strip()
        raw_pause = float(item.get("pause_after", 0.12))
        pause_sec = min(0.16, max(0.08, raw_pause))
        if not spoken_line:
            continue

        line_mp3 = f"temp_clips/tts_parts/line_{i}.mp3"
        used_voice = await synthesize_single_line(spoken_line, voices, line_mp3, rate, pitch)
        line_dur = get_audio_duration(line_mp3)
        print(f"Line {i + 1}/{len(lines_data)} ({used_voice}): {line_dur:.2f}s + {pause_sec:.2f}s breath")

        concat_items.append(line_mp3)

        clean_sub = re.sub(r"[^\w\s.,!?'\"-]", " ", spoken_line)
        words = re.sub(r"\s+", " ", clean_sub).strip().split()
        if words:
            chunk_size = 3
            num_chunks = max(1, (len(words) + chunk_size - 1) // chunk_size)
            chunk_dur = line_dur / num_chunks
            for c in range(0, len(words), chunk_size):
                st = current_time + (c // chunk_size) * chunk_dur
                et = current_time + min(line_dur, ((c // chunk_size) + 1) * chunk_dur)
                phrase = " ".join(words[c : c + chunk_size]).upper()
                srt_lines.append(f"{sub_idx}\n{format_srt_time(st)} --> {format_srt_time(et)}\n{phrase}\n")
                sub_idx += 1

        current_time += line_dur

        if i < len(lines_data) - 1 and pause_sec > 0.04:
            sil_mp3 = f"temp_clips/tts_parts/sil_{i}.mp3"
            subprocess.run(
                [
                    ffmpeg_exe, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", f"{pause_sec:.2f}", "-c:a", "libmp3lame", "-b:a", "64k", sil_mp3
                ],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
            )
            concat_items.append(sil_mp3)
            current_time += pause_sec

    list_txt = "temp_clips/tts_parts/audio_list.txt"
    with open(list_txt, "w") as f:
        for p in concat_items:
            f.write(f"file '{os.path.abspath(p)}'\n")

    subprocess.run(
        [ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", list_txt, "-c:a", "libmp3lame", "-b:a", "128k", audio_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))


async def create_voice_and_subtitles(script_text, voices, audio_path, srt_path, rate="+4%", pitch="+0Hz"):
    clean_text = re.sub(r"[^\w\s.,!?'\"-]", " ", script_text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    word_events = []
    success = False

    for voice in voices:
        for attempt in range(2):
            try:
                word_events = []
                communicate = edge_tts.Communicate(
                    clean_text, voice, rate=rate, pitch=pitch, boundary="WordBoundary"
                )
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


def fetch_guaranteed_emotional_bgm(bgm_out="temp_clips/sad_bgm.mp3"):
    """Guarantees emotional background music on EVERY video (multiple mirrors + synthesized warm ambient pad fallback)."""
    os.makedirs("temp_clips", exist_ok=True)
    bgm_urls = [
        "https://upload.wikimedia.org/wikipedia/commons/e/eb/Beethoven_Moonlight_1st_movement.ogg",
        "https://upload.wikimedia.org/wikipedia/commons/4/4e/Chopin_-_Nocturne_op.9_No.2_E_Flat_Major.ogg",
        "https://upload.wikimedia.org/wikipedia/commons/c/c4/Gymnopedie_No_1.ogg",
        "https://upload.wikimedia.org/wikipedia/commons/b/be/Clair_de_lune_%28Claude_Debussy%29_Suite_bergamasque.ogg",
        "https://upload.wikimedia.org/wikipedia/commons/3/34/Prelude_in_E_minor%2C_Op._28%2C_No._4_%28Chopin%29.ogg",
    ]
    random.shuffle(bgm_urls)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for url in bgm_urls:
        raw_ogg = "temp_clips/raw_bgm.ogg"
        try:
            r = requests.get(url, headers=headers, timeout=25)
            if r.status_code == 200 and len(r.content) > 40000:
                with open(raw_ogg, "wb") as f:
                    f.write(r.content)
                subprocess.run(
                    [ffmpeg_exe, "-y", "-ss", "10", "-i", raw_ogg, "-t", "45", "-c:a", "libmp3lame", "-b:a", "128k", bgm_out],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
                )
                if os.path.exists(bgm_out) and os.path.getsize(bgm_out) > 20000:
                    print(f"Loaded emotional piano BGM: {url.split('/')[-1]}")
                    return bgm_out
        except Exception as e:
            print(f"BGM mirror skip ({url}): {e}")
        finally:
            if os.path.exists(raw_ogg):
                os.remove(raw_ogg)

    # 100% Failsafe: Generate a warm, melancholic minor ambient pad locally via FFmpeg so BGM NEVER fails
    print("Generating failsafe melancholic ambient pad BGM via FFmpeg...")
    synth_expr = (
        "aevalsrc=0.25*sin(2*PI*110*t)+0.20*sin(2*PI*130.81*t)+0.20*sin(2*PI*164.81*t)+0.15*sin(2*PI*220*t)"
        ":s=44100:d=45"
    )
    subprocess.run(
        [
            ffmpeg_exe, "-y", "-f", "lavfi", "-i", synth_expr,
            "-af", "lowpass=f=450,aecho=0.8:0.88:60:0.4",
            "-c:a", "libmp3lame", "-b:a", "128k", bgm_out
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )
    return bgm_out


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


def search_pixabay_hits(queries, fallback_query="sad emotional rain"):
    hits_list = []
    for q in queries:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": PIXABAY_API_KEY, "q": q, "per_page": 10},
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
            params={"key": PIXABAY_API_KEY, "q": fallback_query, "per_page": 10},
            timeout=20,
        )
        for hit in r.json().get("hits", []):
            vids = hit.get("videos", {})
            medium = vids.get("medium") or vids.get("small")
            if medium and medium.get("url"):
                hits_list.append({"url": medium["url"], "tags": hit.get("tags", fallback_query), "duration": 10})
    return hits_list


def build_fast_2s_story_cuts(hook_queries, mid_queries, end_queries, total_dur):
    """Creates fast-paced 2.0-second visual cuts (15+ clips for 30s) matched to Hook, Middle, and Ending."""
    os.makedirs("temp_clips", exist_ok=True)
    clip_len = 2.0
    total_cuts_needed = max(15, int((total_dur + 1.5) / clip_len))

    hook_hits = search_pixabay_hits(hook_queries, fallback_query="sad man rain window")
    mid_hits = search_pixabay_hits(mid_queries, fallback_query="father child emotional")
    end_hits = search_pixabay_hits(end_queries, fallback_query="lonely sunset walking")

    hook_urls = [h["url"] for h in hook_hits] or ["https://pixabay.com/api/videos/"]
    mid_urls = [h["url"] for h in mid_hits] or hook_urls
    end_urls = [h["url"] for h in end_hits] or mid_urls
    random.shuffle(hook_urls)
    random.shuffle(mid_urls)
    random.shuffle(end_urls)

    downloaded_cache = {}
    cut_files = []

    for idx in range(total_cuts_needed):
        progress = idx / max(1, total_cuts_needed)
        if progress < 0.34:
            pool = hook_urls
        elif progress < 0.68:
            pool = mid_urls
        else:
            pool = end_urls

        url = pool[idx % len(pool)]
        if url not in downloaded_cache:
            src_p = f"temp_clips/src_pool_{len(downloaded_cache)}.mp4"
            try:
                with requests.get(url, stream=True, timeout=25) as resp:
                    with open(src_p, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=65536):
                            f.write(chunk)
                if os.path.exists(src_p) and os.path.getsize(src_p) > 15000:
                    downloaded_cache[url] = src_p
            except Exception as e:
                print(f"Source download skip: {e}")
                continue

        src_file = downloaded_cache.get(url)
        if not src_file:
            continue

        cut_p = f"temp_clips/fast2s_{idx:02d}.mp4"
        ss_offset = (idx % 4) * 2.0
        vf = (
            "scale=1160:2060:force_original_aspect_ratio=increase,"
            "crop=1080:1920:x='(iw-1080)/2 + 15*sin(t*1.2)':y='(ih-1920)/2',"
            "eq=contrast=1.12:brightness=-0.04:saturation=0.88,"
            "vignette=PI/4,fps=30"
        )
        cmd = [
            ffmpeg_exe, "-y", "-ss", f"{ss_offset:.1f}", "-stream_loop", "-1", "-i", src_file,
            "-t", f"{clip_len:.1f}", "-an", "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", cut_p
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if os.path.exists(cut_p) and os.path.getsize(cut_p) > 8000:
                cut_files.append(cut_p)
        except Exception as e:
            print(f"2s cut {idx} skip: {e}")

    print(f"Built {len(cut_files)} fast-paced 2.0-second story clips ({len(cut_files) * clip_len:.1f}s total)")
    return cut_files


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


def render_final_video(cut_files, audio_path, srt_path, final_out, bgm_path=None):
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
        "FontName=DejaVu Sans,FontSize=21,Bold=1,PrimaryColour=&H0000FFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=2,Alignment=10"
    )

    if bgm_path and os.path.exists(bgm_path):
        # Clear 22yo Adam-style voice (1.35x) + noticeable emotional BGM (0.22x) on every video
        filter_complex = (
            "[1:a]volume=1.35[voice];"
            "[2:a]volume=0.22,afade=t=in:st=0:d=1.2[bgm];"
            "[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        cmd = [
            ffmpeg_exe, "-y", "-i", merged_bg, "-i", audio_path, "-stream_loop", "-1", "-i", bgm_path,
            "-filter_complex", filter_complex,
            "-vf", f"subtitles={srt_path}:force_style='{subtitle_style}'",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-shortest", final_out
        ]
    else:
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
    bgm_path = None

    if cfg.get("mode") == "deep_life_english_30s":
        # Account 2: 30s English Deep Life Reality & Regret with 22yo Adam-style Realistic Voice, Guaranteed BGM & 2s Cuts
        data = generate_acc2_deep_life_english()
        lines_data = data.get("lines") or []
        tags = " ".join(cfg["hashtags"])
        caption = f"{data['title']} {tags}"

        asyncio.run(
            create_fast_realistic_voice_and_subs(
                lines_data=lines_data,
                voices=cfg["voices"],
                audio_path=audio_path,
                srt_path=srt_path,
                rate=cfg.get("tts_rate", "+9%"),
                pitch=cfg.get("tts_pitch", "+1Hz"),
            )
        )
        dur = get_audio_duration(audio_path)
        print(f"Generated Realistic 22yo Adam-style English voiceover: {dur:.1f}s")

        bgm_path = fetch_guaranteed_emotional_bgm()

        hook_q = data.get("hook_queries") or ["sad man rain window", "looking at phone dark"]
        mid_q = data.get("mid_queries") or ["father holding child", "elderly man working"]
        end_q = data.get("end_queries") or ["lonely sunset walking", "crying emotional person"]
        all_clips = build_fast_2s_story_cuts(hook_q, mid_q, end_q, total_dur=dur)
    else:
        # Account 1 (Usman Edits): 30s 2-Part Curiosity Story (15s AI story intro + 15s mood-matched B-roll)
        data, part_label = generate_acc1_2part_script()
        script_text = data["script"]
        tags = " ".join(cfg["hashtags"])
        caption = f"[{part_label}] {data['title']} {tags}"

        asyncio.run(
            create_voice_and_subtitles(
                tts_text=script_text,
                voices=cfg["voices"],
                audio_path=audio_path,
                srt_path=srt_path,
                rate=cfg.get("tts_rate", "+4%"),
                pitch=cfg.get("tts_pitch", "+0Hz"),
            )
        )
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

    render_final_video(all_clips, audio_path, srt_path, final_video, bgm_path=bgm_path)
    upload_to_zernio(final_video, cfg["account_id"], caption)


if __name__ == "__main__":
    target = os.environ.get("TARGET_ACCOUNT", "acc1")
    run_for_account(target)
