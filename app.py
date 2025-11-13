from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import os

app = Flask(__name__)

# === CONFIGURATION PAR DÉFAUT ===
CONFIG = {
    "target_date": "2025-12-31 23:59:00",
    "font_size": 40,
    "font_color": "#FFFFFF",
    "background_color": "#000000",
    "design": "form"
}


# === ROUTE PAGE D’ACCUEIL ===
@app.route("/")
def index():
    return render_template("index.html", config=CONFIG)


# === ROUTE PAGE DE PARAMÈTRES ===
@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        CONFIG["target_date"] = request.form.get("target_date", CONFIG["target_date"]).replace("T", " ")
        CONFIG["font_size"] = int(request.form.get("font_size", CONFIG["font_size"]))
        CONFIG["font_color"] = request.form.get("font_color", CONFIG["font_color"])
        CONFIG["background_color"] = request.form.get("background_color", CONFIG["background_color"])
        CONFIG["design"] = request.form.get("design", CONFIG["design"])

        # Redirection vers l'accueil après sauvegarde
        return redirect(url_for("index"))

    # Conversion du format pour le champ <input type="datetime-local">
    target_formatted = CONFIG["target_date"]
    try:
        target_formatted = datetime.strptime(target_formatted, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M")
    except:
        pass

    return render_template("settings.html", config=CONFIG, target_date=target_formatted)


# === MODE LOCAL / RENDER ===
if __name__ == "__main__":
    # Render définit un port via la variable d'environnement PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)