from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
import os
import json
import hashlib
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sliqgames-development-key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
GAME_FOLDER = os.path.join(UPLOAD_FOLDER, "games")
THUMB_FOLDER = os.path.join(UPLOAD_FOLDER, "thumbnails")

DATA_FILE = os.path.join(BASE_DIR, "games.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")

os.makedirs(GAME_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)


def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def load_games():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_games(games):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=2)


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


@app.route("/")
def home():
    return render_template(
        "index.html",
        logged_in=("username" in session),
        username=session.get("username")
    )


@app.route("/archer")
def archer():
    return render_template("archer.html")


@app.route("/racing")
def racing():
    return render_template("racing.html")


@app.route("/register", methods=["POST"])
def register():

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if len(username) < 3:
        return "Benutzername muss mindestens 3 Zeichen haben.", 400

    if len(password) < 4:
        return "Passwort muss mindestens 4 Zeichen haben.", 400

    users = load_users()

    for user in users:
        if user["username"].lower() == username.lower():
            return "Dieser Benutzername ist bereits vergeben.", 400

    users.append({
        "username": username,
        "password": hash_password(password)
    })

    save_users(users)

    session["username"] = username

    return redirect(url_for("home"))


@app.route("/login", methods=["POST"])
def login():

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    users = load_users()

    password_hash = hash_password(password)

    for user in users:
        if (
            user["username"].lower() == username.lower()
            and user["password"] == password_hash
        ):
            session["username"] = user["username"]
            return redirect(url_for("home"))

    return "Benutzername oder Passwort falsch.", 401


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


@app.route("/upload", methods=["POST"])
def upload_game():

    if "username" not in session:
        return "Du musst angemeldet sein, um ein Spiel hochzuladen.", 403

    name = request.form.get("name", "").strip()
    genre = request.form.get("genre", "").strip()
    description = request.form.get("description", "").strip()

    game_file = request.files.get("game")
    thumbnail = request.files.get("thumbnail")

    if not name or not genre or not description:
        return "Bitte ALLE Felder ausfüllen!", 400

    if not game_file or not thumbnail:
        return "Spiel-Datei und Thumbnail werden benötigt.", 400

    game_filename = secure_filename(game_file.filename)
    thumb_filename = secure_filename(thumbnail.filename)

    if not game_filename or not thumb_filename:
        return "Ungültige Datei.", 400

    game_file.save(os.path.join(GAME_FOLDER, game_filename))
    thumbnail.save(os.path.join(THUMB_FOLDER, thumb_filename))

    games = load_games()

    games.append({
        "name": name,
        "genre": genre,
        "description": description,
        "game": game_filename,
        "thumbnail": thumb_filename,
        "creator": session["username"]
    })

    save_games(games)

    return redirect(url_for("home"))


@app.route("/games.json")
def games_json():

    games = load_games()

    return json.dumps(games, ensure_ascii=False), 200, {
        "Content-Type": "application/json"
    }


@app.route("/uploads/thumbnails/<filename>")
def thumbnail(filename):
    return send_from_directory(THUMB_FOLDER, filename)


@app.route("/uploads/games/<filename>")
def game_file(filename):
    return send_from_directory(GAME_FOLDER, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
