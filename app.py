import os
import json
import sys
import uuid
from functools import wraps
from datetime import datetime, timedelta
from io import BytesIO

from flask import (
    Flask,
    send_file,
    request,
    render_template,
    url_for,
    redirect,
    session,
)
from PIL import Image, ImageDraw, ImageFont
from json import JSONDecodeError

# ============================
# CONFIG GLOBALE
# ============================
DEFAULT_CONFIG = {
    "width": 600,
    "height": 200,
    "background_color": "#FFFFFF",
    "text_color": "#000000",
    "font_path": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "font_size": 40,
    "message_prefix": "Temps restant : ",
    "target_date": "2025-12-31T23:59:59",
    "loop_duration": 10,
}

CONFIG_DIR = "configs"              # Dossier où on stocke les JSON de chaque countdown
ADMIN_PASSWORD = "Doudou2904!!"     # Mot de passe admin
SECRET_KEY_DEFAULT = "change-me-secret"  # À changer en prod si tu veux


# ============================
# OUTILS UTILITAIRES
# ============================
def ensure_configs_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def countdown_path(countdown_id: str) -> str:
    return os.path.join(CONFIG_DIR, f"{countdown_id}.json")


def load_countdown_config(countdown_id: str):
    """
    Charge la config d'un countdown depuis configs/<id>.json.
    Retourne un dict ou None si introuvable / invalide.
    """
    ensure_configs_dir()
    path = countdown_path(countdown_id)
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("config not a dict")
    except (JSONDecodeError, ValueError) as e:
        print(f"⚠️ Erreur lecture config {countdown_id}.json :", e, file=sys.stderr)
        return None

    cfg = DEFAULT_CONFIG.copy()
    cfg.update(data)
    return cfg


def save_countdown_config(countdown_id: str, cfg: dict):
    """
    Sauvegarde la config d'un countdown sous configs/<id>.json.
    """
    ensure_configs_dir()
    path = countdown_path(countdown_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def list_countdowns():
    """
    Retourne la liste des countdowns disponibles sous forme de dicts :
    {
      "id": ...,
      "path": ...,
      "mtime": datetime,
      "gif_url": ...,
      "preview_url": ...
    }
    """
    ensure_configs_dir()
    items = []
    for filename in os.listdir(CONFIG_DIR):
        if not filename.endswith(".json"):
            continue
        cid = filename[:-5]
        path = countdown_path(cid)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
        except OSError:
            mtime = None
        items.append(
            {
                "id": cid,
                "path": path,
                "mtime": mtime,
            }
        )
    # Tri du plus récent au plus ancien
    items.sort(key=lambda x: x["mtime"] or datetime.min, reverse=True)
    return items


# ============================
# FLASK APP & SÉCURITÉ ADMIN
# ============================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", SECRET_KEY_DEFAULT)


def is_admin():
    return session.get("is_admin") is True


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not is_admin():
            # Redirige vers /admin avec "next" stocké
            next_url = request.path
            return redirect(url_for("admin_login", next=next_url))
        return view_func(*args, **kwargs)
    return wrapper


# ============================
# ROUTES ADMIN
# ============================
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    error = None
    next_url = request.args.get("next") or url_for("admin_list")

    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(next_url)
        else:
            error = "Mot de passe incorrect."

    return render_template("admin.html", error=error)


@app.route("/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("create_countdown"))


# ============================
# CRÉATION D'UN NOUVEAU COUNTDOWN
# ============================
@app.route("/", methods=["GET", "POST"])
def create_countdown():
    """
    Page principale : formulaire pour créer un nouveau compte à rebours.
    À chaque POST, on génère un nouvel ID + fichier JSON, et on affiche le lien.
    """
    cfg = DEFAULT_CONFIG.copy()
    img_link = None
    countdown_id = None

    if request.method == "POST":
        # Récupération des valeurs du formulaire
        raw_date = request.form.get("target_date", "").strip()
        if raw_date:
            # Format HTML datetime-local : "YYYY-MM-DDTHH:MM"
            if len(raw_date) == 16:
                raw_date = raw_date + ":00"
            raw_date = raw_date.replace(" ", "T")
            cfg["target_date"] = raw_date

        cfg["background_color"] = request.form.get("background_color", cfg["background_color"])
        cfg["text_color"] = request.form.get("text_color", cfg["text_color"])

        try:
            cfg["font_size"] = int(request.form.get("font_size", cfg["font_size"]))
        except ValueError:
            pass

        cfg["message_prefix"] = request.form.get("message_prefix", cfg["message_prefix"])

        # Génération d'un ID unique (8 caractères hex)
        countdown_id = uuid.uuid4().hex[:8]
        save_countdown_config(countdown_id, cfg)

        # Lien complet vers l'image dynamique pour cet ID
        base = request.url_root.rstrip("/")
        img_link = base + url_for("countdown_image", countdown_id=countdown_id)

    # Préparation de la date pour l'input HTML
    td = cfg.get("target_date", DEFAULT_CONFIG["target_date"])
    try:
        dt = datetime.fromisoformat(td)
        target_date_for_input = dt.strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        target_date_for_input = DEFAULT_CONFIG["target_date"][:16]

    return render_template(
        "settings.html",
        config=cfg,
        target_date=target_date_for_input,
        img_link=img_link,
        countdown_id=countdown_id,
    )


@app.route("/settings")
def redirect_settings():
    return redirect(url_for("create_countdown"))


# ============================
# LISTE DES COUNTDOWNS (ADMIN)
# ============================
@app.route("/list")
@admin_required
def admin_list():
    items = list_countdowns()
    base = request.url_root.rstrip("/")
    enriched = []
    for it in items:
        cid = it["id"]
        enriched.append(
            {
                "id": cid,
                "mtime": it["mtime"],
                "gif_url": base + url_for("countdown_image", countdown_id=cid),
                "preview_url": base + url_for("preview_countdown", countdown_id=cid),
                "export_url": base + url_for("export_countdown", countdown_id=cid),
            }
        )
    return render_template("list.html", countdowns=enriched)


# ============================
# PREVIEW D'UN COUNTDOWN (ADMIN)
# ============================
@app.route("/preview/<countdown_id>")
@admin_required
def preview_countdown(countdown_id):
    cfg = load_countdown_config(countdown_id)
    if cfg is None:
        return "Compte à rebours introuvable", 404

    base = request.url_root.rstrip("/")
    gif_url = base + url_for("countdown_image", countdown_id=countdown_id)

    td = cfg.get("target_date", DEFAULT_CONFIG["target_date"])
    try:
        dt = datetime.fromisoformat(td)
        target_date_for_input = dt.strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        target_date_for_input = DEFAULT_CONFIG["target_date"][:16]

    return render_template(
        "preview.html",
        countdown_id=countdown_id,
        config=cfg,
        target_date=target_date_for_input,
        gif_url=gif_url,
    )


# ============================
# EXPORT / IMPORT (ADMIN)
# ============================
@app.route("/export/<countdown_id>")
@admin_required
def export_countdown(countdown_id):
    path = countdown_path(countdown_id)
    if not os.path.exists(path):
        return "Compte à rebours introuvable", 404

    return send_file(
        path,
        mimetype="application/json",
        as_attachment=True,
        download_name=f"{countdown_id}.json",
    )


@app.route("/import", methods=["POST"])
@admin_required
def import_countdown():
    """
    Import via textarea JSON + ID optionnel.
    """
    raw_json = request.form.get("import_json", "").strip()
    custom_id = request.form.get("import_id", "").strip() or None

    if not raw_json:
        return redirect(url_for("admin_list"))

    try:
        data = json.loads(raw_json)
        if not isinstance(data, dict):
            raise ValueError("JSON doit représenter un objet")
    except Exception:
        # On pourrait afficher un message d'erreur, pour simplifier on revient à /list
        return redirect(url_for("admin_list"))

    if custom_id:
        countdown_id = custom_id
    else:
        countdown_id = uuid.uuid4().hex[:8]

    cfg = DEFAULT_CONFIG.copy()
    cfg.update(data)
    save_countdown_config(countdown_id, cfg)

    return redirect(url_for("admin_list"))


# ============================
# SUPPRESSION D'UN COUNTDOWN (ADMIN)
# ============================
@app.route("/delete/<countdown_id>", methods=["POST"])
@admin_required
def delete_countdown(countdown_id):
    path = countdown_path(countdown_id)
    if os.path.exists(path):
        os.remove(path)
    return redirect(url_for("admin_list"))


# ============================
# GÉNÉRATION DU GIF DYNAMIQUE
# ============================
@app.route("/c/<countdown_id>.gif")
def countdown_image(countdown_id):
    """
    Génère le GIF pour un compte à rebours donné (ID).
    URL typique : /c/ab93f12c.gif
    """
    cfg = load_countdown_config(countdown_id)
    if cfg is None:
        return "Compte à rebours introuvable", 404

    loop_duration = cfg.get("loop_duration", 10)

    try:
        end_time = datetime.fromisoformat(cfg["target_date"])
    except ValueError:
        return "Date invalide dans la configuration", 400

    now = datetime.utcnow()
    frames = []

    for i in range(loop_duration):
        current_time = now + timedelta(seconds=i)
        remaining = int((end_time - current_time).total_seconds())

        if remaining <= 0:
            text = "⏰ Terminé !"
        else:
            days, rem = divmod(remaining, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, seconds = divmod(rem, 60)
            text = f"{cfg['message_prefix']}{days}j {hours:02}:{minutes:02}:{seconds:02}"

        img = Image.new("RGB", (cfg["width"], cfg["height"]), cfg["background_color"])
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(cfg["font_path"], cfg["font_size"])
        except Exception:
            font = ImageFont.load_default()

        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (cfg["width"] - text_width) // 2
        y = (cfg["height"] - text_height) // 2
        draw.text((x, y), text, font=font, fill=cfg["text_color"])

        frames.append(img)

    buf = BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=1000,
    )
    buf.seek(0)
    return send_file(buf, mimetype="image/gif")


# ============================
# LANCEMENT SERVEUR
# ============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
