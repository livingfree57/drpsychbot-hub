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

if __name__ == "__main__":
    os.makedirs(KB_DIR, exist_ok=True)
    app.run(debug=True, port=5001)


