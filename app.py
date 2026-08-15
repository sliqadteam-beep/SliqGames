from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sliqgames-development-key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
GAME_FOLDER = os.path.join(UPLOAD_FOLDER, "games")
THUMB_FOLDER = os.path.join(UPLOAD_FOLDER, "thumbnails")
DATA_FILE = os.path.join(BASE_DIR, "games.json")

os.makedirs(GAME_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

ALLOWED_GAME_EXTENSIONS = {"html", "htm"}
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

GENRES = [
    "Action",
    "Adventure",
    "Arcade",
    "Puzzle",
    "Strategy",
    "Sports",
    "Racing",
    "Horror",
    "Funny",
    "Other"
]

@app.route("/")
def home():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        games = json.load(f)

    return render_template("index.html", games=games)


@app.route("/upload-game", methods=["POST"])
def upload_game():

    name = request.form.get("name", "").strip()
    genre = request.form.get("genre", "").strip()
    game_file = request.files.get("game_file")
    thumbnail = request.files.get("thumbnail")

    # ALLES MUSS AUSGEFÜLLT WERDEN
    if not name or not genre or not game_file or not thumbnail:
        return "Bitte alle Felder ausfüllen.", 400

    if genre not in GENRES:
        return "Ungültiges Genre.", 400

    game_filename = secure_filename(game_file.filename)
    thumbnail_filename = secure_filename(thumbnail.filename)

    if not game_filename or not thumbnail_filename:
        return "Ungültige Dateien.", 400

    game_ext = game_filename.rsplit(".", 1)[-1].lower()
    image_ext = thumbnail_filename.rsplit(".", 1)[-1].lower()

    if game_ext not in ALLOWED_GAME_EXTENSIONS:
        return "Das Spiel muss eine HTML-Datei sein.", 400

    if image_ext not in ALLOWED_IMAGE_EXTENSIONS:
        return "Das Thumbnail muss PNG, JPG, JPEG oder WEBP sein.", 400

    safe_name = secure_filename(name.lower().replace(" ", "-"))

    final_game_name = safe_name + ".html"
    final_thumbnail_name = safe_name + "." + image_ext

    game_path = os.path.join(GAME_FOLDER, final_game_name)
    thumbnail_path = os.path.join(THUMB_FOLDER, final_thumbnail_name)

    game_file.save(game_path)
    thumbnail.save(thumbnail_path)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        games = json.load(f)

    games.append({
        "name": name,
        "genre": genre,
        "game": final_game_name,
        "thumbnail": final_thumbnail_name
    })

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)

    return redirect(url_for("home"))


@app.route("/games/<filename>")
def serve_game(filename):
    return send_from_directory(GAME_FOLDER, filename)


@app.route("/thumbnails/<filename>")
def serve_thumbnail(filename):
    return send_from_directory(THUMB_FOLDER, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
