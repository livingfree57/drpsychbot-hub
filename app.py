

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
    user_input = data.get("message", "").strip()
    selected_bot = data.get("bot", "")

    if not hasattr(voice_reply, "conversation_history"):
        voice_reply.conversation_history = []

    # Load topic-specific KB
    kb_files = get_bot_kb(selected_bot)
    bot_kb = []
    if kb_files and kb_files["json"]:
        try:
            with open(kb_files["json"], "r", encoding="utf-8") as f:
                bot_kb = json.load(f)
        except Exception as e:
            print("Error loading bot KB:", e)

    # --- Helper Functions ---
    def detect_question_intent(text):
        keywords = ["what is", "can you tell me", "explain", "define", "how does", "how can", "why does"]
        return any(keyword in text.lower() for keyword in keywords)

    def detect_requesting_advice(text):
        advice_keywords = ["what should i do", "how do i fix", "can you help me fix", "any suggestions", "how can i solve"]
        return any(keyword in text.lower() for keyword in advice_keywords)

    # Try KB first
    reply = ""
    close_matches = difflib.get_close_matches(
        user_input.lower(), 
        [entry["question"].lower() for entry in bot_kb], 
        n=1, 
        cutoff=0.6
    )
    if close_matches:
        reply = next(
            (entry["answer"] for entry in bot_kb if entry["question"].lower() == close_matches[0]), ""
        )

    # GPT Fallback if no KB match
    if not reply:
        try:
            # Build conversation context
            history = voice_reply.conversation_history[-8:]  # last 8 turns max
            system_message = {
                "role": "system",
                "content": (
                    "You are a calm, empathic listener trained in reflective psychotherapy. "
                    "First, mirror the user's emotional state warmly, without validating by saying it is normal or okay to feel that way. "
                    "If the user clearly asks for advice (using words like 'what should I do?', 'can you help me fix this?'), "
                    "then gently offer one encouraging, non-overwhelming suggestion. "
                    "If the user requests specific information (using words like 'tell me', 'can you tell me', 'give me information'), "
                    "then offer detailed information based on your best knowledge. "
                    "Otherwise, stay with their emotions, helping them feel heard and safe. "
                    "Keep responses concise and caring, within 2–3 short sentences."
                )
            }

            messages = [system_message] + history + [{"role": "user", "content": user_input}]
            gpt_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=120
            )
            reply = gpt_response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print("GPT fallback error:", e)
            reply = "I'm here to listen if you want to share more."

    # Update conversation history
    voice_reply.conversation_history.append({"role": "user", "content": user_input})
    voice_reply.conversation_history.append({"role": "assistant", "content": reply})

    # Limit history to last 10 turns
    if len(voice_reply.conversation_history) > 20:
        voice_reply.conversation_history = voice_reply.conversation_history[-20:]

    # Voice generation (ElevenLabs)
    try:
        audio_filename = f"response_{uuid.uuid4().hex}.mp3"
        audio_path = pathlib.Path("static") / audio_filename

        audio = client_11.text_to_speech.convert(
            text=reply,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        save(audio, str(audio_path))

        return jsonify({"text": reply, "audio_url": f"/static/{audio_filename}"})
    except Exception as e:
        print("ElevenLabs voice error:", e)
        return jsonify({"text": reply})




if __name__ == "__main__":
    if not os.environ.get("RENDER"):
        KB_DIR.mkdir(parents=True, exist_ok=True)
        app.run(debug=True, port=5001)


