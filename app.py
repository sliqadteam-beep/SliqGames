```python
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, jsonify
import os
import json
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "sliqgames-development-key-change-this"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
GAME_FOLDER = os.path.join(UPLOAD_FOLDER, "games")
THUMB_FOLDER = os.path.join(UPLOAD_FOLDER, "thumbnails")

DATA_FILE = os.path.join(BASE_DIR, "games.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")

os.makedirs(GAME_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)


# =========================================================
# DATEIEN ERSTELLEN
# =========================================================

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)


if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)


# =========================================================
# HILFSFUNKTIONEN
# =========================================================

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


# =========================================================
# STARTSEITE
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# ARCHER HERO
# =========================================================

@app.route("/archer")
def archer():
    return render_template("archer.html")


# =========================================================
# NEON RACING
# =========================================================

@app.route("/racing")
def racing():
    return render_template("racing.html")


# =========================================================
# ACCOUNT STATUS
# =========================================================

@app.route("/api/me")
def current_user():

    username = session.get("username")

    if not username:
        return jsonify({
            "logged_in": False
        })

    return jsonify({
        "logged_in": True,
        "username": username
    })


# =========================================================
# REGISTRIEREN
# =========================================================

@app.route("/api/register", methods=["POST"])
def register():

    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or not password:
        return jsonify({
            "success": False,
            "message": "Bitte Benutzername und Passwort eingeben."
        }), 400

    if len(username) < 3:
        return jsonify({
            "success": False,
            "message": "Der Benutzername muss mindestens 3 Zeichen haben."
        }), 400

    if len(password) < 6:
        return jsonify({
            "success": False,
            "message": "Das Passwort muss mindestens 6 Zeichen haben."
        }), 400

    users = load_users()

    for user in users:
        if user["username"].lower() == username.lower():
            return jsonify({
                "success": False,
                "message": "Dieser Benutzername ist bereits vergeben."
            }), 400

    users.append({
        "username": username,
        "password": generate_password_hash(password)
    })

    save_users(users)

    session["username"] = username

    return jsonify({
        "success": True,
        "username": username
    })


# =========================================================
# ANMELDEN
# =========================================================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    users = load_users()

    for user in users:

        if user["username"].lower() == username.lower():

            if check_password_hash(user["password"], password):

                session["username"] = user["username"]

                return jsonify({
                    "success": True,
                    "username": user["username"]
                })

            break

    return jsonify({
        "success": False,
        "message": "Benutzername oder Passwort falsch."
    }), 401


# =========================================================
# LOGOUT
# =========================================================

@app.route("/api/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "success": True
    })


# =========================================================
# SPIEL HOCHLADEN
# =========================================================

@app.route("/upload", methods=["POST"])
def upload_game():

    # -----------------------------------------------------
    # ACCOUNT PFLICHT
    # -----------------------------------------------------

    username = session.get("username")

    if not username:
        return """
        <script>
        alert("Du musst angemeldet sein, um ein Spiel hochzuladen.");
        window.location.href="/";
        </script>
        """, 401

    # -----------------------------------------------------
    # FORMULAR
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # DATEIEN SPEICHERN
    # -----------------------------------------------------

    game_file.save(
        os.path.join(GAME_FOLDER, game_filename)
    )

    thumbnail.save(
        os.path.join(THUMB_FOLDER, thumb_filename)
    )

    # -----------------------------------------------------
    # SPIEL SPEICHERN
    # -----------------------------------------------------

    games = load_games()

    games.append({
        "name": name,
        "genre": genre,
        "description": description,
        "game": game_filename,
        "thumbnail": thumb_filename,

        # Creator wird automatisch aus Account übernommen
        "creator": username
    })

    save_games(games)

    return redirect(url_for("home"))


# =========================================================
# SPIELE API
# =========================================================

@app.route("/games.json")
def games_json():

    games = load_games()

    return jsonify(games)


# =========================================================
# THUMBNAILS
# =========================================================

@app.route("/uploads/thumbnails/<filename>")
def thumbnail(filename):

    return send_from_directory(
        THUMB_FOLDER,
        filename
    )


# =========================================================
# SPIELDATEIEN
# =========================================================

@app.route("/uploads/games/<filename>")
def game_file(filename):

    return send_from_directory(
        GAME_FOLDER,
        filename
    )


# =========================================================
# SERVER START
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )
```
