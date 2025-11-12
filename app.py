import os
import json
from datetime import datetime
from flask import Flask, send_file, request, render_template, redirect, url_for
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# ----------- CONFIGURATION -----------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "width": 600,
        "height": 200,
        "background_color": "#F5F5F5",
        "text_color": "#222222",
        "font_path": "templates/DejaVuSans.ttf"
        "font_size": 40,
        "message_prefix": "Temps restante : ",
        "target_date": "2025-12-31T23:59:59",
        "loop_duration": 40
    }

def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

CONFIG = load_config()

# ----------- PAGE PRINCIPALE -----------
@app.route("/")
def home():
    return """
    <h2>Mon Compte à Rebours</h2>
    <img src='/countdown.gif' alt='countdown'>
    <br><a href='/settings'>⚙️ Configurer</a>
    """

# ----------- PAGE SETTINGS -----------
@app.route("/settings", methods=["GET", "POST"])
def settings():
    global CONFIG
    if request.method == "POST":
        CONFIG["target_date"] = request.form.get("target_date", CONFIG["target_date"])
        CONFIG["background_color"] = request.form.get("background_color", CONFIG["background_color"])
        CONFIG["text_color"] = request.form.get("text_color", CONFIG["text_color"])
        CONFIG["font_size"] = int(request.form.get("font_size", CONFIG["font_size"]))
        CONFIG["message_prefix"] = request.form.get("message_prefix", CONFIG["message_prefix"])

        print("✅ Nouvelle configuration :", CONFIG)  # Debug

        save_config(CONFIG)
        return redirect(url_for("countdown_gif") + "?_=" + str(datetime.utcnow().timestamp()))

    return render_template("settings.html", config=CONFIG)

# ----------- GÉNÉRATION DU GIF -----------
@app.route("/countdown.gif")
def countdown():
    config = load_config()
    now = datetime.now()
    target = datetime.fromisoformat(config["target_date"])
    delta = target - now

    # Calcul du temps restant
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)