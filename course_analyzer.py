import os
import re
import glob
import json
import time
import subprocess
import gdown
import imageio_ffmpeg
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
COURSE_DRIVE_URL = os.environ["COURSE_DRIVE_URL"].strip()

client = genai.Client(api_key=GEMINI_API_KEY)
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()


def download_course_videos(drive_input):
    os.makedirs("course_videos", exist_ok=True)
    links = [u.strip() for u in drive_input.split(",") if u.strip()]

    for idx, link in enumerate(links):
        print(f"Downloading from Drive ({idx + 1}/{len(links)}): {link}")
        if "/folders/" in link:
            gdown.download_folder(url=link, output="course_videos", quiet=False, use_cookies=False)
        else:
            gdown.download(url=link, output=f"course_videos/video_{idx + 1}.mp4", quiet=False, fuzzy=True)

    video_exts = ("*.mp4", "*.mkv", "*.mov", "*.avi", "*.webm")
    files = []
    for ext in video_exts:
        files.extend(glob.glob(f"course_videos/**/{ext}", recursive=True))
    return sorted(list(set(files)))


def extract_compressed_audio(video_path, index):
    audio_out = f"course_audio_{index}.mp3"
    print(f"Extracting lightweight audio from {os.path.basename(video_path)}...")
    # 16kHz mono 24kbps shrinks 4-hour video into ~40MB MP3 for fast Gemini upload
    cmd = [
        ffmpeg_exe, "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "24k",
        audio_out
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return audio_out


def analyze_single_module(audio_path, module_num):
    print(f"Uploading Module {module_num} audio to Gemini AI...")
    uploaded = client.files.upload(file=audio_path)

    while uploaded.state.name == "PROCESSING":
        print("Waiting for Gemini to process audio...")
        time.sleep(10)
        uploaded = client.files.get(name=uploaded.name)

    prompt = f"""
    You are an expert TikTok Creator Rewards Program (USA & UK) strategist and automation architect.
    Listen carefully to the ENTIRE Module {module_num} of this TikTok Monetization Zero-to-Advance course.
    Extract EVERY actionable strategy, rule, secret, editing style, hook formula, RPM tip, account warm-up rule, and monetization requirement taught by the instructor.

    Return a thorough, structured breakdown covering:
    1. Core TikTok Creator Rewards (USA/UK) rules & eligibility secrets taught here.
    2. Best high-RPM niches mentioned or implied by the instructor's framework.
    3. Exact video structure (duration > 1 min, hook timing, pacing, voiceover, visuals, captions, music).
    4. Algorithm growth, posting frequency, shadowban prevention, and account setup rules.
    5. Specific tools, assets, or accounts needed to automate this exact workflow.
    """

    for model_name in ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.1-flash-lite"]:
        try:
            print(f"Analyzing Module {module_num} with {model_name}...")
            res = client.models.generate_content(
                model=model_name,
                contents=[uploaded, prompt]
            )
            client.files.delete(name=uploaded.name)
            return res.text
        except Exception as e:
            print(f"{model_name} error: {e}")
            time.sleep(5)

    raise Exception(f"Failed to analyze Module {module_num}")


def build_final_blueprint_and_requirements(module_notes):
    combined = "\n\n====================\n\n".join(
        f"### MODULE {i + 1} NOTES ###\n{note}" for i, note in enumerate(module_notes)
    )

    master_prompt = f"""
    Based on the complete TikTok Monetization Zero-to-Advance course notes below, create TWO outputs in valid JSON:
    1. "requirements_markdown": A clear, complete Markdown guide titled "TIKTOK USA/UK CREATOR REWARDS BOT - BLUEPRINT & REQUIREMENTS" containing:
       - **3 Best High-RPM Niches** tailored to the course's exact method (designed for USA/UK audiences & 1-minute+ Creator Rewards eligibility).
       - **Exact Video Production Formula** for each of the 3 niches (script style, hook, visuals, voiceover, length, captions, and posting schedule).
       - **EXACT REQUIREMENTS CHECKLIST FOR THE USER**: List every single item the user needs to provide so our 24/7 GitHub bot can run autonomously (e.g., 3 USA/UK TikTok accounts, TikTok Content Posting API / Pipedream webhook tokens, AI voice/video preferences, etc.).
    2. "course_rules_json": A structured machine-readable JSON object containing the 3 chosen niches, exact prompt templates, video duration rules, hashtag rules, and posting schedules so Phase 2 (`tiktok_autopilot.py`) can execute them automatically 24/7.

    Course Notes:
    {combined}

    Return ONLY valid JSON with keys "requirements_markdown" and "course_rules_json".
    """

    res = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=master_prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    return json.loads(res.text)


if __name__ == "__main__":
    videos = download_course_videos(COURSE_DRIVE_URL)
    if not videos:
        raise Exception("No videos found! Check that your Google Drive link is set to 'Anyone with the link can view'.")

    print(f"Found {len(videos)} course video(s):", videos)
    all_notes = []

    for idx, v_path in enumerate(videos):
        audio_file = extract_compressed_audio(v_path, idx + 1)
        notes = analyze_single_module(audio_file, idx + 1)
        all_notes.append(notes)
        if os.path.exists(v_path):
            os.remove(v_path)
        if os.path.exists(audio_file):
            os.remove(audio_file)

    final_data = build_final_blueprint_and_requirements(all_notes)

    with open("REQUIREMENTS.md", "w", encoding="utf-8") as f:
        f.write(final_data["requirements_markdown"])

    with open("course_rules.json", "w", encoding="utf-8") as f:
        json.dump(final_data["course_rules_json"], f, indent=2)

    print("SUCCESS! Generated REQUIREMENTS.md and course_rules.json in your repository!")
