

from flask import Flask, request, jsonify, render_template
import os
import csv
import json
import pathlib
import difflib
import uuid
import openai
from elevenlabs import save
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# ── KNOWLEDGE-BASE CONFIG ─────────────────────────────────────────
KB_DIR = pathlib.Path(__file__).parent / "kb"
ROUTING_CONFIG_FILE = KB_DIR / "drpsychbot_routing_config.json"

# Load empathy KB
with (KB_DIR / "empathic_counseling_json.json").open("r", encoding="utf-8") as f:
    EMPATHY_KB = json.load(f)

# Load bot routing config
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

# ElevenLabs & OpenAI setup
client_11 = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")
voice_id = os.getenv("VOICE_ID")

# ── ROUTES ─────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/drkim")
def drkim():
    return render_template("drkim.html")

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
    selected_bot = data.get("bot", "")
    final_reply = ""

    # Load bot KB
    bot_kb = []
    kb_files = get_bot_kb(selected_bot)
    if kb_files and kb_files["json"]:
        try:
            with open(kb_files["json"], "r", encoding="utf-8") as f:
                bot_kb = json.load(f)
        except Exception as e:
            print("Error loading bot KB:", e)

    # Helper Functions
    def detect_question_intent(text):
        informational_keywords = ["what is", "can you tell me", "explain", "define", "help me understand", "how does", "how can", "why does"]
        return any(keyword in text for keyword in informational_keywords)

    def detect_short_affirmation(text):
        affirmations = ["yes", "yeah", "yep", "right", "correct", "that's right", "exactly", "sure", "of course"]
        return text.strip() in affirmations

    # Short Affirmation Handling
    if detect_short_affirmation(user_input):
        final_reply = "I'm hearing that you agree. Thank you for sharing that."
    else:
        is_informational = detect_question_intent(user_input)
        info_reply = ""
        empathy_reply = ""

        if is_informational:
            info_match = difflib.get_close_matches(user_input, [e["question"].lower() for e in bot_kb], n=1, cutoff=0.6)
            if info_match:
                info_reply = next((e["answer"] for e in bot_kb if e["question"].lower() == info_match[0]), "")
            if not info_reply:
                empathy_match = difflib.get_close_matches(user_input, [e["question"].lower() for e in EMPATHY_KB], n=1, cutoff=0.6)
                if empathy_match:
                    empathy_reply = next((e["answer"] for e in EMPATHY_KB if e["question"].lower() == empathy_match[0]), "")
        else:
            empathy_match = difflib.get_close_matches(user_input, [e["question"].lower() for e in EMPATHY_KB], n=1, cutoff=0.6)
            if empathy_match:
                empathy_reply = next((e["answer"] for e in EMPATHY_KB if e["question"].lower() == empathy_match[0]), "")
            if not empathy_reply:
                info_match = difflib.get_close_matches(user_input, [e["question"].lower() for e in bot_kb], n=1, cutoff=0.6)
                if info_match:
                    info_reply = next((e["answer"] for e in bot_kb if e["question"].lower() == info_match[0]), "")

        if info_reply:
            final_reply = info_reply
        elif empathy_reply:
            final_reply = empathy_reply
        else:
            try:
                gpt_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    temperature=0.7,
                    max_tokens=60,
                    messages=[
                        {"role": "system", "content": (
                            "You are a calm, empathic listener trained in reflective psychotherapy. "
                "First, mirror the user's emotional state warmly, without validating by saying it is normal or okay to feel that way. "
                "If the user clearly asks for advice (using words like 'what should I do?' or 'can you help me fix this?'), "
                "then gently offer one encouraging, non-overwhelming suggestion. "
                "Otherwise, stay with their emotions, helping them feel heard and safe. "
                "Keep responses concise and caring, within 2–3 short sentences."
                        )},
                        {"role": "user", "content": user_input}
                             ]
                )
                final_reply = gpt_response["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print("GPT fallback error:", e)
                final_reply = "I'm here to listen, even if I don't have the perfect words yet."

    # ElevenLabs voice generation
    try:
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
    if not os.environ.get("RENDER"):
        KB_DIR.mkdir(parents=True, exist_ok=True)
        app.run(debug=True, port=5001)


