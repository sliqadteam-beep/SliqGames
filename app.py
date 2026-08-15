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


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/archer")
def archer():
    return render_template("archer.html")


@app.route("/racing")
def racing():
    return render_template("racing.html")


@app.route("/upload", methods=["POST"])
def upload_game():

    name = request.form.get("name", "").strip()
    genre = request.form.get("genre", "").strip()
    description = request.form.get("description", "").strip()

    game_file = request.files.get("game")
    thumbnail = request.files.get("thumbnail")

    if not name or not genre or not description or not game_file or not thumbnail:
        return "Bitte ALLE Felder ausfüllen!", 400

    game_filename = secure_filename(game_file.filename)
    thumb_filename = secure_filename(thumbnail.filename)

    if not game_filename or not thumb_filename:
        return "Ungültige Datei.", 400

    game_file.save(os.path.join(GAME_FOLDER, game_filename))
    thumbnail.save(os.path.join(THUMB_FOLDER, thumb_filename))

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            games = json.load(f)
    except:
        games = []

    games.append({
        "name": name,
        "genre": genre,
        "description": description,
        "game": game_filename,
        "thumbnail": thumb_filename
    })

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=2)

    return redirect(url_for("home"))


@app.route("/games.json")
def games_json():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return f.read(), 200, {"Content-Type": "application/json"}
    except:
        return "[]", 200, {"Content-Type": "application/json"}


@app.route("/uploads/thumbnails/<filename>")
def thumbnail(filename):
    return send_from_directory(THUMB_FOLDER, filename)


@app.route("/uploads/games/<filename>")
def game_file(filename):
    return send_from_directory(GAME_FOLDER, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
