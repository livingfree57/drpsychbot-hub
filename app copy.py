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

app = Flask(__name__)

# ── KNOWLEDGE-BASE CONFIG ─────────────────────────────────────────
KB_DIR = pathlib.Path(__file__).parent / "kb"
ROUTING_CONFIG_FILE = KB_DIR / "drpsychbot_routing_config.json"

with open(ROUTING_CONFIG_FILE, "r", encoding="utf-8") as f:
    BOT_CONFIGS = json.load(f)

# Helper to get bot KB paths
def get_bot_kb(bot_name):
    for bot in BOT_CONFIGS:
        if bot["bot_name"].lower() == bot_name.lower():
            return {
                "csv": KB_DIR / bot["kb_csv"],
                "json": KB_DIR / bot["kb_json"]
            }
    return None

# ELEVENLABS & OPENAI SETUP
client_11 = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")
voice_id      = os.getenv("VOICE_ID")

@app.route("/")
def index():
    
    return render_template("index.html")

@app.route("/list-bots")
def list_bots():
    return jsonify([
        {
            "bot": b["bot_name"],
            "category": b["category"],
            "description": b["description"]
        } for b in BOT_CONFIGS
    ])

@app.route("/voice", methods=["POST"])
def voice_reply():
    data = request.json
    user_input = data.get("message", "").strip().lower()
    bot_name = data.get("bot")

    kb_files = get_bot_kb(bot_name)
    if not kb_files:
        return jsonify({"text": "I couldn't find that topic. Please try another.", "audio_url": ""})

    try:
        with open(kb_files["json"], "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except:
        json_data = []

    json_triggers = [entry["question"].strip().lower() for entry in json_data]

    for entry in json_data:
        q = entry["question"]
        reflection = f"It sounds like you're wondering, \"{q}\" — and that’s a really important question. "
        if not entry["answer"].startswith("It sounds like"):
            entry["answer"] = reflection + entry["answer"]

    # Load CSV if exists
    csv_data = []
    try:
        with open(kb_files["csv"], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                csv_data.append({
                    "question": row["question"].strip().lower(),
                    "answer": row["answer"].strip()
                })
    except:
        pass


    json_hit = None
    csv_hit  = None

    closest = difflib.get_close_matches(user_input, json_triggers, n=1, cutoff=0.7)
    print("🔍 Closest trigger:", closest)
    if closest:
        trg = closest[0]
        for entry in json_data:
            if entry["question"].strip().lower() == trg:
                json_hit = entry["answer"]
                for follow in entry.get("follow_up", []):
                    if follow["keyword"].strip().lower() in user_input:
                        json_hit += " " + follow["response"]
                break

    if not json_hit:
        for item in csv_data:
            q = item["question"]
            if q in user_input or user_input in q:
                csv_hit = item["answer"]
                break

    gpt_text = ""
    if not json_hit and not csv_hit:
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role":"system","content":"You’re a counselor with expertise in unspoken and unaddressed silent trauma. Reply in 2–3 brief paragraphs, plain language."},
                    {"role":"user","content":user_input}
                ],
                max_tokens=200
            )
            gpt_text = resp.choices[0].message.content.strip()
        except Exception as e:
            print("❌ GPT error:", e)
            gpt_text = "I'm still learning. Would you like to try asking in a different way?"

    if json_hit:
        final_reply = f"{json_hit}\n\n{gpt_text}".strip()
    elif csv_hit:
        final_reply = f"{csv_hit}\n\n{gpt_text}".strip()
    else:
        final_reply = gpt_text

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

if __name__ == "__main__":
    os.makedirs(KB_DIR, exist_ok=True)
    app.run(debug=True, port=5001)

