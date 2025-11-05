import os
import json
import sys
from datetime import datetime, timedelta
from io import BytesIO
from flask import Flask, send_file, request, render_template, redirect, url_for
from PIL import Image, ImageDraw, ImageFont
from json import JSONDecodeError

# ============================
# Configuration par défaut
# ============================
DEFAULT_CONFIG = {
    "width": 600,
    "height": 200,
    "background_color": "#F5F5F5",
    "text_color": "#222222",
    "font_path": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "font_size": 40,
    "message_prefix": "Temps restant : ",
    "target_date": "2025-12-31T23:59:59",
    "loop_duration": 40
}

CONFIG_PATH = "config.json"
# Test auto-deploy Render

def load_config():
    cfg = DEFAULT_CONFIG.copy()

    # Lecture depuis les variables d'environnement
    cfg["target_date"] = os.getenv("TARGET_DATE", cfg["target_date"])
    cfg["background_color"] = os.getenv("BACKGROUND_COLOR", cfg["background_color"])
    cfg["text_color"] = os.getenv("TEXT_COLOR", cfg["text_color"])
    cfg["font_size"] = int(os.getenv("FONT_SIZE", cfg["font_size"]))
    cfg["message_prefix"] = os.getenv("MESSAGE_PREFIX", cfg["message_prefix"])

    return cfg


def save_config(cfg):
    """Ne rien faire ici sur Render (lecture seule), juste log."""
    print("🟢 Nouvelle configuration (non enregistrée sur fichier) :")
    print(json.dumps(cfg, indent=2, ensure_ascii=False))


CONFIG = load_config()

# ============================
# App Flask
# ============================
app = Flask(__name__)

@app.route("/")
def home():
    return (
        "<h2>🕒 Countdown Generator</h2>"
        "<p><a href='/settings'>Configurer le design</a></p>"
        "<p><img src='/countdown.gif' alt='Countdown GIF'></p>"
    )

@app.route("/settings", methods=["GET", "POST"])
def settings():
    global CONFIG

    if request.method == "POST":
        # Si la requête vient de JavaScript (application/json)
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        CONFIG["target_date"] = data.get("target_date", CONFIG["target_date"])
        CONFIG["background_color"] = data.get("background_color", CONFIG["background_color"])
        CONFIG["text_color"] = data.get("text_color", CONFIG["text_color"])
        CONFIG["font_size"] = int(data.get("font_size", CONFIG["font_size"]))
        CONFIG["message_prefix"] = data.get("message_prefix", CONFIG["message_prefix"])

        save_config(CONFIG)
        return ("", 204)  # Réponse vide mais succès

    return render_template("settings.html", config=CONFIG)



@app.route("/countdown.gif")
def countdown_gif():
    cfg = load_config()
    loop_duration = cfg.get("loop_duration", 40)
    try:
        end_time = datetime.fromisoformat(cfg["target_date"])
    except ValueError:
        return "Date invalide dans config.json", 400

    now = datetime.utcnow()
    frames = []

    for i in range(loop_duration):
        current_time = now + timedelta(seconds=i)
        remaining = int((end_time - current_time).total_seconds())

        if remaining <= 0:
            text = "⏰ La date est dépassée !"
        else:
            days, rem = divmod(remaining, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, seconds = divmod(rem, 60)
            text = f"{cfg['message_prefix']}{days}j {hours:02}:{minutes:02}:{seconds:02}"

        img = Image.new("RGB", (cfg["width"], cfg["height"]), cfg["background_color"])
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(cfg["font_path"], cfg["font_size"])
        except:
            font = ImageFont.load_default()

        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (cfg["width"] - text_width) // 2
        y = (cfg["height"] - text_height) // 2
        draw.text((x, y), text, font=font, fill=cfg["text_color"])

        frames.append(img)

    buf = BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], loop=0, duration=1000)
    buf.seek(0)
    return send_file(buf, mimetype="image/gif")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
