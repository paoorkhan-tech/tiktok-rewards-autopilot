# TIKTOK USA/UK CREATOR REWARDS BOT - BLUEPRINT & REQUIREMENTS

## 1. 3 Best High-RPM Niches (USA/UK Creator Rewards Targeted)

### Niche 1: Relationship & Psychology Drama (Reddit Stories)
- **Why it Works:** Extremely high retention and watch-through rate past the 60-second mark. Targets US/UK adult demographics with high advertiser spending, yielding high RPMs ($0.80 - $1.50+).
- **RPM Potential:** Very High ($0.80–$1.50+)
- **Target Audience:** USA/UK adults (18–45) interested in drama, advice, and relationship stories.

### Niche 2: ASMR / Satisfying & Experimental Destruction
- **Why it Works:** Kinetic sand, soap crushing, and hydraulic press content rely on visual curiosity and sensory tension. Viewers naturally watch the full 60+ seconds to see the final payoff, maintaining high completion rates.
- **RPM Potential:** Medium-High ($0.50–$0.90)
- **Target Audience:** Broad USA/UK audience, high engagement, save & share heavy.

### Niche 3: Home Cleaning, Restocking & Restoration
- **Why it Works:** Visually satisfying step-by-step transformations (fridge restocking, deep cleaning dirty homes, shoe restoration). Keeps viewers fixated and appeals to adult demographics with disposable income.
- **RPM Potential:** High ($0.70–$1.20)
- **Target Audience:** USA/UK adults (21–50) focused on lifestyle, home improvement, and organization.

---

## 2. Exact Video Production Formula

### Formula 1: Relationship & Psychology Drama
- **Duration:** 65 to 75 seconds (Must strictly exceed 60s).
- **Script Style:** Storytelling derived from viral Reddit posts (`r/Relationship_Advice`), rewritten via AI for viral pacing (Hook -> Context -> Escalation -> Cliffhanger/Climax).
- **Hook (0-3s):** No title card. Immediate shocking statement: *"My husband kept a secret phone inside our living room wall for three years, and what I found on it ruined everything."*
- **Visuals:** Dynamic background B-roll (satisfying kinetic sand cutting, Minecraft parkour, or ASMR footage). Mirror clips, alter speeds (1.05x), apply color grade to prevent unoriginality flags. Clip length: 2-3 seconds max per visual transition.
- **Voiceover:** ElevenLabs natural human voice (e.g., "Adam" or "Rachel"), dynamic pitch, no monotone standard TikTok robot voices.
- **Captions:** Center-aligned, high-contrast yellow/white dynamic single-word or short-phrase captions with heavy shadow.
- **Posting Schedule:** 2 posts daily (14:00 UTC and 20:00 UTC / Target US Eastern peak hours).

### Formula 2: Satisfying Visuals & ASMR Destruction
- **Duration:** 65 to 70 seconds.
- **Script Style:** Process curiosity script or high-fidelity raw ASMR with contextual narration.
- **Hook (0-3s):** Immediate visual action teasing the outcome: *"Will a 100-ton hydraulic press completely vaporize solid brass, or will it explode? Watch till the end."*
- **Visuals:** High-resolution close-up macro clips (hydraulic press crushing objects, soap slicing). Speed ramp transitions (fast to slow motion at impact point).
- **Voiceover:** Deep, engaging male narrator AI voice or amplified raw audio with brief setup commentary.
- **Captions:** Bold top/bottom screen callout text asking viewers to comment their predictions.
- **Posting Schedule:** 2 posts daily (16:00 UTC and 22:00 UTC).

### Formula 3: Home Cleaning & Restocking
- **Duration:** 68 to 80 seconds.
- **Script Style:** Transformation journey with step-by-step progress counters.
- **Hook (0-3s):** Fast visual preview of the filthy "before" and clean "after" with voiceover: *"This was declared the dirtiest apartment in London, and I have exactly 6 hours to clean it."*
- **Visuals:** Fast-paced cleaning clips, fridge restocking sequences, micro-cuts every 1.5 to 2.5 seconds. Mirror visual orientation and add custom visual filters to satisfy originality algorithms.
- **Voiceover:** Upbeat, conversational human-like AI voice.
- **Captions:** High-contrast step indicators (e.g., "STEP 1: DEEP SCRUB") centered on screen.
- **Posting Schedule:** 1 post daily (18:00 UTC).

---

## 3. EXACT REQUIREMENTS CHECKLIST FOR THE USER
To allow our 24/7 GitHub bot (`tiktok_autopilot.py`) to execute fully autonomously, the user must provide the following inputs:

- [ ] **3 Monetized / Monetization-Ready TikTok Accounts:**
  - Regions: USA or UK strictly.
  - Age verified 18+.
  - Warmed up (at least 48 hours of manual liking/scrolling in target niche prior to bot automation).
- [ ] **TikTok Content Posting API / Access Credentials:**
  - API Tokens or Pipedream Webhook Endpoints configured for posting to each account.
- [ ] **Dedicated Residential USA/UK Proxies:**
  - HTTP/SOCKS5 proxy per account (IP must stay static to US/UK to protect CRP eligibility and prevent shadowbans).
- [ ] **ElevenLabs API Key & Voice IDs:**
  - Valid API Key with active character quota.
  - Voice IDs selected for Storytelling, ASMR Narration, and Upbeat Lifestyle.
- [ ] **OpenAI / Anthropic API Key:**
  - API Key for GPT-4 / Claude-3.5-Sonnet to execute script generation and re-writing prompts autonomously.
- [ ] **Asset Storage & B-Roll Library Access:**
  - Google Drive / AWS S3 / Cloudinary bucket link containing tagged B-roll folders (`kinetic_sand`, `cleaning_clips`, `destruction_hd`, `satisfying_loops`).
- [ ] **Configuration Settings File (`config.env` / GitHub Secrets):**
  - `ELEVENLABS_API_KEY`
  - `OPENAI_API_KEY`
  - `TIKTOK_POSTING_WEBHOOK_URL_ACC1`
  - `TIKTOK_POSTING_WEBHOOK_URL_ACC2`
  - `TIKTOK_POSTING_WEBHOOK_URL_ACC3`
  - `US_PROXY_ADDRESS_1`, `US_PROXY_ADDRESS_2`, `UK_PROXY_ADDRESS_1`