"""
drrolandbot_voice.py
Hybrid text‑plus‑voice Flask bot
–––––––––––––––––––––––––––––––
"""

        #!/usr/bin/env python3
import os
import csv
import json
import pathlib
import difflib
import uuid

from flask import Flask, request, jsonify, render_template
import openai
from elevenlabs import save
from elevenlabs.client import ElevenLabs

# ── APP SETUP ────────────────────────────────────────────────────────
app = Flask(__name__)

# ── KNOWLEDGE‑BASE PATHS ─────────────────────────────────────────────
KB_DIR    = pathlib.Path(__file__).parent / "kb"
CSV_FILE  = KB_DIR / "silent_trauma_csv.csv"   # <-- adjust filename
JSON_FILE = KB_DIR / "silent_trauma_json.json"         # <-- adjust filename

# ── LOAD CSV KB ────────────────────────────────────────────────────
csv_data = []
with CSV_FILE.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # normalize question to lowercase for matching
        csv_data.append({
            "question": row["question"].strip().lower(),
            "answer":   row["answer"].strip()
        })

# ── LOAD JSON KB ───────────────────────────────────────────────────
with JSON_FILE.open("r", encoding="utf-8") as f:
    json_data = json.load(f)

# build a lowercase trigger list once
json_triggers = [entry["question"].strip().lower() for entry in json_data]

# ── ELEVENLABS & OPENAI SETUP ─────────────────────────────────────
client_11 = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")
voice_id      = os.getenv("VOICE_ID")

# ── ROUTES ─────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("drrolandbot.html")


@app.route("/voice", methods=["POST"])
def voice_reply():
    user_input = request.json.get("message", "").strip().lower()
    print("🎙 USER:", user_input)

    json_hit = None
    csv_hit  = None

    # 1️⃣ JSON fuzzy‐match (cutoff=0.7)
    closest = difflib.get_close_matches(user_input, json_triggers, n=1, cutoff=0.7)
    print("🔍 Closest trigger:", closest)
    if closest:
        trg = closest[0]
        for entry in json_data:
            if entry["question"].strip().lower() == trg:
                json_hit = entry["answer"]
                # optional follow‑ups
                for follow in entry.get("follow_up", []):
                    if follow["keyword"].strip().lower() in user_input:
                        json_hit += " " + follow["response"]
                break

    # 2️⃣ CSV fallback
    if not json_hit:
        for item in csv_data:
            q = item["question"]
            if q in user_input or user_input in q:
                csv_hit = item["answer"]
                break

    # 3️⃣ GPT fallback
    gpt_text = ""
    if not json_hit and not csv_hit:
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role":"system","content":"You’re an empathetic trauma therapist. Reply in 2–3 brief paragraphs, plain language."},
                    {"role":"user","content":user_input}
                ],
                max_tokens=200
            )
            gpt_text = resp.choices[0].message.content.strip()
        except Exception as e:
            print("❌ GPT error:", e)
            gpt_text = (
                "I’m here to help, but I couldn’t find an answer right now. "
                "Could you try rephrasing your question?"
            )

    # 4️⃣ Stitch final_reply
    if json_hit:
        final_reply = f"{json_hit}\n\n{gpt_text}".strip()
    elif csv_hit:
        final_reply = f"{csv_hit}\n\n{gpt_text}".strip()
    else:
        final_reply = gpt_text

    # ── Voice synthesis ───────────────────────────────────────────────
    audio_filename = f"response_{uuid.uuid4().hex}.mp3"
    audio_path     = pathlib.Path("static") / audio_filename

    audio = client_11.text_to_speech.convert(
        text          = final_reply,
        voice_id      = voice_id,
        model_id      = "eleven_multilingual_v2",
        output_format = "mp3_44100_128"
    )
    save(audio, str(audio_path))

    return jsonify({"text": final_reply, "audio_url": f"/static/{audio_filename}"})


# ── MAIN ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)

