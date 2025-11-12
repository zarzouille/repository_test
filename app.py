import os
import json
from datetime import datetime
from flask import Flask, render_template, request, send_file, redirect, url_for
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

CONFIG_PATH = "config.json"

# --- 1️⃣ Chargement de la configuration ---
def load_config():
    """Charge le fichier de configuration ou renvoie les valeurs par défaut."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Erreur de lecture du config.json — fichier réinitialisé.")
    # Valeurs par défaut
    return {
        "target_date": "2025-12-31T23:59",
        "background_color": "#000000",
        "text_color": "#FFFFFF",
        "font_size": 40,
        "message_prefix": "Temps restant :"
    }

CONFIG = load_config()

# --- 2️⃣ Sauvegarde de la config ---
def save_config():
    """Sauvegarde la configuration actuelle dans le fichier JSON."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(CONFIG, f, indent=2)

# --- 3️⃣ Page principale ---
@app.route("/")
def index():
    return render_template("index.html", config=CONFIG)

# --- 4️⃣ Page de configuration ---
@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        CONFIG["target_date"] = request.form.get("target_date")
        CONFIG["background_color"] = request.form.get("background_color")
        CONFIG["text_color"] = request.form.get("text_color")
        CONFIG["font_size"] = int(request.form.get("font_size") or 40)
        CONFIG["message_prefix"] = request.form.get("message_prefix", "Temps restant :")
        save_config()
        return redirect(url_for("index"))
    return render_template("settings.html", config=CONFIG)

# --- 5️⃣ Génération dynamique du GIF ---
@app.route("/countdown.gif")
def countdown_gif():
    """Crée dynamiquement une image GIF représentant le compte à rebours."""
    try:
        target = datetime.strptime(CONFIG["target_date"], "%Y-%m-%dT%H:%M")
        remaining = target - datetime.now()
        if remaining.total_seconds() < 0:
            text = "Terminé !"
        else:
            days = remaining.days
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            text = f"{CONFIG['message_prefix']} {days}j {hours}h {minutes}m {seconds}s"

        # Création de l'image
        img = Image.new("RGB", (800, 200), CONFIG["background_color"])
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", CONFIG["font_size"])
        except IOError:
            font = ImageFont.load_default()

        # Calcul pour centrer le texte
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text(
            ((800 - text_w) / 2, (200 - text_h) / 2),
            text,
            fill=CONFIG["text_color"],
            font=font,
        )

        img.save("countdown.gif", "GIF")
        return send_file("countdown.gif", mimetype="image/gif")

    except Exception as e:
        print(f"❌ Erreur dans countdown_gif : {e}")
        return "Erreur lors de la génération du GIF.", 500


# --- 6️⃣ Exécution locale (et compatibilité Render) ---
if __name__ == "__main__":
    # Render définit le port via la variable d'environnement PORT
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Application démarrée sur http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)