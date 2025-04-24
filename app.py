

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

from dotenv import load_dotenv

load_dotenv()  



kb_path = "kb/"
target_names = ["DrRolandBot", "DrParentingBot", "DrTeenagerBot"]
replacement = "DrPsychBot"

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
    
@app.route("/about")
def about():
    return render_template("about.html")


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
    user_input = data.get("message", "")
    selected_bot = data.get("bot", "")

    # Load knowledge base (as you're already doing)
    kb_files = get_bot_kb(selected_bot)
    final_reply = None

    if kb_files:
        try:
            with open(kb_files["json"], "r", encoding="utf-8") as f:
                bot_kb = json.load(f)
            for item in bot_kb:
                if user_input.lower() in item["question"].lower():
                    final_reply = item["answer"]
                    break
        except Exception as e:
            print("KB load error:", e)

    # GPT fallback
    if not final_reply:
        try:
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            gpt_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a compassionate AI therapist."},
                    {"role": "user", "content": user_input}
                ]
            )
            final_reply = gpt_response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("GPT fallback error:", e)
            final_reply = "I'm here to support you, but I couldn’t reach my knowledge source right now."

    # ElevenLabs voice (wrapped in try/except)
    try:
        import uuid
        from elevenlabs import save
        from elevenlabs.client import ElevenLabs

        voice_id = os.getenv("VOICE_ID", "your_default_voice_id")  # optional
        client_11 = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))

        audio_filename = f"response_{uuid.uuid4().hex}.mp3"
        audio_path = pathlib.Path("static") / audio_filename

        audio = client_11.text_to_speech.convert(
            text=final_reply,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        save(audio, str(audio_path))

        return jsonify({"text": final_reply, "audio_url": f"/static/{audio_filename}"})

    except Exception as e:
        print("ElevenLabs voice error:", e)
        return jsonify({"text": final_reply})

if __name__ == "__main__":
    import os
    if not os.environ.get("RENDER"):
        from pathlib import Path
        KB_DIR.mkdir(parents=True, exist_ok=True)
        app.run(debug=True, port=5001)


