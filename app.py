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

    # ----- NOUVELLES OPTIONS AVANCÉES -----
    "template": "classic",                 # classic, blocks, minimal, bubble, flip, banner, progress

    "show_labels": True,                   # J / H / M / S
    "labels_custom": False,                # si True, utilise labels_personalized
    "label_color": "#444444",
    "label_size_factor": 0.5,             # taille labels relative à font_size
    "labels_personalized": {
        "days": "Jours",
        "hours": "Heures",
        "minutes": "Minutes",
        "seconds": "Secondes"
    },

    "block_bg_color": "#FFFFFF",
    "block_border_color": "#000000",
    "block_border_width": 2,
    "block_radius": 12,
    "block_padding_x": 16,
    "block_padding_y": 8,
    "blocks_gap": 12,

    "alignment": "center",                # left, center, right
    "padding": 20,

    "icon": "🕒",                         # peut être vide ""
    "icon_position": "left",              # left, right, above

    # Progress bar options
    "progress_bg_color": "#EEEEEE",
    "progress_fg_color": "#00AAFF",
    "progress_height": 16,
    "progress_max_days": 30,              # fenêtre max pour la progression

    # Banner
    "banner_bg_color": "#222222",
    "banner_text_color": "#FFFFFF",
}

CONFIG_DIR = "configs"                    # dossier où on stocke les JSON de chaque countdown
ADMIN_PASSWORD = "Doudou2904!!"           # Mot de passe admin
SECRET_KEY_DEFAULT = "change-me-secret"   # À changer en prod si tu veux


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

    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy safe
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
    { "id": ..., "mtime": datetime }
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
        items.append({"id": cid, "mtime": mtime})
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
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    img_link = None
    countdown_id = None

    if request.method == "POST":
        # Récupération des valeurs du formulaire
        raw_date = request.form.get("target_date", "").strip()
        if raw_date:
            if len(raw_date) == 16:
                raw_date = raw_date + ":00"
            raw_date = raw_date.replace(" ", "T")
            cfg["target_date"] = raw_date

        cfg["background_color"] = request.form.get("background_color", cfg["background_color"])
        cfg["text_color"] = request.form.get("text_color", cfg["text_color"])
        cfg["font_size"] = int(request.form.get("font_size", cfg["font_size"]) or cfg["font_size"])
        cfg["message_prefix"] = request.form.get("message_prefix", cfg["message_prefix"])

        # Template & layout
        cfg["template"] = request.form.get("template", cfg["template"])
        cfg["alignment"] = request.form.get("alignment", cfg["alignment"])
        cfg["padding"] = int(request.form.get("padding", cfg["padding"]) or cfg["padding"])

        # Labels
        cfg["show_labels"] = (request.form.get("show_labels") == "on")
        cfg["labels_custom"] = (request.form.get("labels_custom") == "on")
        cfg["label_color"] = request.form.get("label_color", cfg["label_color"])
        try:
            cfg["label_size_factor"] = float(request.form.get("label_size_factor", cfg["label_size_factor"]))
        except ValueError:
            pass

        if cfg["labels_custom"]:
            cfg["labels_personalized"]["days"] = request.form.get("label_days", cfg["labels_personalized"]["days"])
            cfg["labels_personalized"]["hours"] = request.form.get("label_hours", cfg["labels_personalized"]["hours"])
            cfg["labels_personalized"]["minutes"] = request.form.get("label_minutes", cfg["labels_personalized"]["minutes"])
            cfg["labels_personalized"]["seconds"] = request.form.get("label_seconds", cfg["labels_personalized"]["seconds"])

        # Blocks
        cfg["block_bg_color"] = request.form.get("block_bg_color", cfg["block_bg_color"])
        cfg["block_border_color"] = request.form.get("block_border_color", cfg["block_border_color"])
        cfg["block_border_width"] = int(request.form.get("block_border_width", cfg["block_border_width"]) or cfg["block_border_width"])
        cfg["block_radius"] = int(request.form.get("block_radius", cfg["block_radius"]) or cfg["block_radius"])
        cfg["block_padding_x"] = int(request.form.get("block_padding_x", cfg["block_padding_x"]) or cfg["block_padding_x"])
        cfg["block_padding_y"] = int(request.form.get("block_padding_y", cfg["block_padding_y"]) or cfg["block_padding_y"])
        cfg["blocks_gap"] = int(request.form.get("blocks_gap", cfg["blocks_gap"]) or cfg["blocks_gap"])

        # Icon
        cfg["icon"] = request.form.get("icon", cfg["icon"])
        cfg["icon_position"] = request.form.get("icon_position", cfg["icon_position"])

        # Progress
        cfg["progress_bg_color"] = request.form.get("progress_bg_color", cfg["progress_bg_color"])
        cfg["progress_fg_color"] = request.form.get("progress_fg_color", cfg["progress_fg_color"])
        cfg["progress_height"] = int(request.form.get("progress_height", cfg["progress_height"]) or cfg["progress_height"])
        cfg["progress_max_days"] = int(request.form.get("progress_max_days", cfg["progress_max_days"]) or cfg["progress_max_days"])

        # Banner
        cfg["banner_bg_color"] = request.form.get("banner_bg_color", cfg["banner_bg_color"])
        cfg["banner_text_color"] = request.form.get("banner_text_color", cfg["banner_text_color"])

        # Génération d'un ID unique
        countdown_id = uuid.uuid4().hex[:8]
        save_countdown_config(countdown_id, cfg)

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
        cfg = load_countdown_config(cid) or {}
        template_name = cfg.get("template", "classic")
        enriched.append(
            {
                "id": cid,
                "mtime": it["mtime"],
                "gif_url": base + url_for("countdown_image", countdown_id=cid),
                "preview_url": base + url_for("preview_countdown", countdown_id=cid),
                "export_url": base + url_for("export_countdown", countdown_id=cid),
                "template": template_name,
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
    raw_json = request.form.get("import_json", "").strip()
    custom_id = request.form.get("import_id", "").strip() or None

    if not raw_json:
        return redirect(url_for("admin_list"))

    try:
        data = json.loads(raw_json)
        if not isinstance(data, dict):
            raise ValueError("JSON doit représenter un objet")
    except Exception:
        return redirect(url_for("admin_list"))

    if custom_id:
        countdown_id = custom_id
    else:
        countdown_id = uuid.uuid4().hex[:8]

    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    cfg.update(data)
    save_countdown_config(countdown_id, cfg)

    return redirect(url_for("admin_list"))


@app.route("/delete/<countdown_id>", methods=["POST"])
@admin_required
def delete_countdown(countdown_id):
    path = countdown_path(countdown_id)
    if os.path.exists(path):
        os.remove(path)
    return redirect(url_for("admin_list"))


# ============================
# RENDU DES TEMPLATES POUR LE GIF
# ============================
def draw_center_text(img, draw, cfg, text, font):
    w, h = cfg["width"], cfg["height"]
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (w - tw) // 2
    y = (h - th) // 2
    draw.text((x, y), text, font=font, fill=cfg["text_color"])


def draw_classic(draw, img, cfg, font, days, hours, minutes, seconds):
    icon = cfg.get("icon", "")
    prefix = cfg.get("message_prefix", "")
    text = f"{prefix}{days}j {hours:02}:{minutes:02}:{seconds:02}"
    if icon:
        if cfg.get("icon_position") == "left":
            text = f"{icon} {text}"
        elif cfg.get("icon_position") == "right":
            text = f"{text} {icon}"
        elif cfg.get("icon_position") == "above":
            # On dessine l'icône au-dessus séparément
            w, h = cfg["width"], cfg["height"]
            icon_font = font
            bbox_icon = draw.textbbox((0, 0), icon, font=icon_font)
            iw = bbox_icon[2] - bbox_icon[0]
            ih = bbox_icon[3] - bbox_icon[1]
            ix = (w - iw) // 2
            iy = cfg["padding"]
            draw.text((ix, iy), icon, font=icon_font, fill=cfg["text_color"])
            # On réduit la zone dispo pour le texte
            bbox_text = draw.textbbox((0, 0), text, font=font)
            tw = bbox_text[2] - bbox_text[0]
            th = bbox_text[3] - bbox_text[1]
            tx = (w - tw) // 2
            ty = iy + ih + 10
            draw.text((tx, ty), text, font=font, fill=cfg["text_color"])
            return
    draw_center_text(img, draw, cfg, text, font)


def draw_blocks_like(draw, img, cfg, font, days, hours, minutes, seconds, shape="rect"):
    """
    shape: "rect", "flip", "bubble"
    """
    w, h = cfg["width"], cfg["height"]
    padding = cfg["padding"]
    units = [
        ("days", days),
        ("hours", hours),
        ("minutes", minutes),
        ("seconds", seconds),
    ]

    labels = cfg["labels_personalized"] if cfg.get("labels_custom") else {
        "days": "J",
        "hours": "H",
        "minutes": "M",
        "seconds": "S",
    }

    show_labels = cfg.get("show_labels", True)
    label_color = cfg.get("label_color", "#444444")
    label_size = int(cfg["font_size"] * float(cfg.get("label_size_factor", 0.5)) or 1)
    try:
        label_font = ImageFont.truetype(cfg["font_path"], label_size)
    except Exception:
        label_font = ImageFont.load_default()

    block_bg = cfg["block_bg_color"]
    block_border = cfg["block_border_color"]
    border_w = cfg["block_border_width"]
    radius = cfg["block_radius"]
    pad_x = cfg["block_padding_x"]
    pad_y = cfg["block_padding_y"]
    gap = cfg["blocks_gap"]

    # Mesure des blocs
    blocks_info = []
    for key, value in units:
        txt = f"{value:02}"
        tb = draw.textbbox((0, 0), txt, font=font)
        tw = tb[2] - tb[0]
        th = tb[3] - tb[1]

        label = labels.get(key, key.upper())
        if show_labels:
            lb = draw.textbbox((0, 0), label, font=label_font)
            lw = lb[2] - lb[0]
            lh = lb[3] - lb[1]
        else:
            lw = lh = 0

        bw = max(tw, lw) + pad_x * 2
        bh = th + (lh if show_labels else 0) + pad_y * 3

        blocks_info.append({
            "key": key,
            "value": value,
            "text": txt,
            "label": label,
            "bw": bw,
            "bh": bh,
            "tw": tw,
            "th": th,
            "lw": lw,
            "lh": lh,
        })

    total_width = sum(b["bw"] for b in blocks_info) + gap * (len(blocks_info) - 1)
    x_start = (w - total_width) // 2
    y_center = h // 2

    # Dessin
    x = x_start
    for b in blocks_info:
        bw = b["bw"]
        bh = b["bh"]
        top = y_center - bh // 2
        bottom = top + bh

        if shape == "bubble":
            # cercle / ellipse
            draw.ellipse(
                (x, top, x + bw, bottom),
                fill=block_bg,
                outline=block_border,
                width=border_w,
            )
        else:
            # rect / flip
            draw.rounded_rectangle(
                (x, top, x + bw, bottom),
                radius=radius,
                fill=block_bg,
                outline=block_border,
                width=border_w,
            )
            if shape == "flip":
                mid = (top + bottom) // 2
                draw.line((x, mid, x + bw, mid), fill=block_border, width=1)

        # texte principal
        text_x = x + (bw - b["tw"]) // 2
        text_y = top + pad_y
        draw.text((text_x, text_y), b["text"], font=font, fill=cfg["text_color"])

        # label en dessous
        if show_labels:
            label_x = x + (bw - b["lw"]) // 2
            label_y = bottom - pad_y - b["lh"]
            draw.text((label_x, label_y), b["label"], font=label_font, fill=label_color)

        x += bw + gap


def draw_minimal(draw, img, cfg, font, days, hours, minutes, seconds):
    text = f"{days:02}:{hours:02}:{minutes:02}:{seconds:02}"
    draw_center_text(img, draw, cfg, text, font)


def draw_banner(draw, img, cfg, font, days, hours, minutes, seconds):
    w, h = cfg["width"], cfg["height"]
    padding = cfg["padding"]
    bg = cfg["banner_bg_color"]
    fg = cfg["banner_text_color"]
    prefix = cfg["message_prefix"]

    # fond
    draw.rounded_rectangle(
        (padding, padding, w - padding, h - padding),
        radius=cfg["block_radius"],
        fill=bg,
    )

    text = f"{prefix}{days} jours {hours:02}h {minutes:02}m {seconds:02}s"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (w - tw) // 2
    y = (h - th) // 2
    draw.text((x, y), text, font=font, fill=fg)


def draw_progress(draw, img, cfg, font, days, hours, minutes, seconds, remaining, total_initial):
    w, h = cfg["width"], cfg["height"]
    padding = cfg["padding"]

    bg = cfg["progress_bg_color"]
    fg = cfg["progress_fg_color"]
    ph = cfg["progress_height"]

    # calcul progression
    if total_initial <= 0:
        ratio = 1.0
    else:
        ratio = 1.0 - max(remaining, 0) / total_initial
    ratio = max(0.0, min(1.0, ratio))

    bar_left = padding
    bar_right = w - padding
    bar_top = h // 2 - ph // 2
    bar_bottom = bar_top + ph

    # fond de barre
    draw.rounded_rectangle(
        (bar_left, bar_top, bar_right, bar_bottom),
        radius=ph // 2,
        fill=bg,
    )

    # partie remplie
    fill_right = bar_left + int((bar_right - bar_left) * ratio)
    draw.rounded_rectangle(
        (bar_left, bar_top, fill_right, bar_bottom),
        radius=ph // 2,
        fill=fg,
    )

    # texte dessous
    prefix = cfg.get("message_prefix", "")
    text = f"{prefix}{days}j {hours:02}:{minutes:02}:{seconds:02}"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (w - tw) // 2
    y = bar_bottom + 8
    if y + th < h - padding:
        draw.text((x, y), text, font=font, fill=cfg["text_color"])


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
    total_initial = max(int((end_time - now).total_seconds()), 1)

    frames = []
    for i in range(loop_duration):
        current_time = now + timedelta(seconds=i)
        remaining = int((end_time - current_time).total_seconds())

        img = Image.new("RGB", (cfg["width"], cfg["height"]), cfg["background_color"])
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype(cfg["font_path"], cfg["font_size"])
        except Exception:
            font = ImageFont.load_default()

        if remaining <= 0:
            # Terminé pour tous les templates = simple texte
            draw_center_text(img, draw, cfg, "⏰ Terminé !", font)
        else:
            total_seconds = remaining
            days, rem = divmod(total_seconds, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, seconds = divmod(rem, 60)

            template = cfg.get("template", "classic")

            if template == "classic":
                draw_classic(draw, img, cfg, font, days, hours, minutes, seconds)
            elif template == "blocks":
                draw_blocks_like(draw, img, cfg, font, days, hours, minutes, seconds, shape="rect")
            elif template == "flip":
                draw_blocks_like(draw, img, cfg, font, days, hours, minutes, seconds, shape="flip")
            elif template == "bubble":
                draw_blocks_like(draw, img, cfg, font, days, hours, minutes, seconds, shape="bubble")
            elif template == "minimal":
                draw_minimal(draw, img, cfg, font, days, hours, minutes, seconds)
            elif template == "banner":
                draw_banner(draw, img, cfg, font, days, hours, minutes, seconds)
            elif template == "progress":
                draw_progress(draw, img, cfg, font, days, hours, minutes, seconds, remaining, total_initial)
            else:
                # fallback
                draw_classic(draw, img, cfg, font, days, hours, minutes, seconds)

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
