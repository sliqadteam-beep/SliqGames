from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "sliqgames-development-key"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
GAME_FOLDER = os.path.join(UPLOAD_FOLDER, "games")
THUMB_FOLDER = os.path.join(UPLOAD_FOLDER, "thumbnails")

DATA_FILE = os.path.join(BASE_DIR, "games.json")

os.makedirs(GAME_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)


# =========================================================
# ERLAUBTE GENRES
# =========================================================

ALLOWED_GENRES = [
    "Action",
    "Adventure",
    "Arcade",
    "Casual",
    "Horror",
    "Racing",
    "Sports",
    "Strategy",
    "Funny",
    "Other"
]


# =========================================================
# GAMES.JSON ERSTELLEN
# =========================================================

if not os.path.exists(DATA_FILE):

    with open(DATA_FILE, "w", encoding="utf-8") as f:

        json.dump(
            [],
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# STARTSEITE
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# SPIELE ABRUFEN
# =========================================================

@app.route("/games.json")
def games_json():

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            games = json.load(f)

    except Exception:

        games = []

    return jsonify(games)


# =========================================================
# SPIEL HOCHLADEN
# =========================================================

@app.route("/upload", methods=["POST"])
def upload_game():

    name = request.form.get(
        "name",
        ""
    ).strip()

    genre = request.form.get(
        "genre",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    game_file = request.files.get(
        "game"
    )

    thumbnail = request.files.get(
        "thumbnail"
    )


    # -----------------------------------------------------
    # ALLES AUSFÜLLEN
    # -----------------------------------------------------

    if not name:

        return "Bitte einen Spielnamen eingeben.", 400


    if not genre:

        return "Bitte ein Genre auswählen.", 400


    if not description:

        return "Bitte eine Beschreibung eingeben.", 400


    if not game_file or not game_file.filename:

        return "Bitte eine Spieldatei auswählen.", 400


    if not thumbnail or not thumbnail.filename:

        return "Bitte ein Thumbnail auswählen.", 400


    # -----------------------------------------------------
    # GENRE PRÜFEN
    # -----------------------------------------------------

    if genre not in ALLOWED_GENRES:

        return "Ungültiges Genre.", 400


    # -----------------------------------------------------
    # DATEINAMEN SICHERN
    # -----------------------------------------------------

    game_filename = secure_filename(
        game_file.filename
    )

    thumb_filename = secure_filename(
        thumbnail.filename
    )


    if not game_filename:

        return "Ungültige Spieldatei.", 400


    if not thumb_filename:

        return "Ungültiges Thumbnail.", 400


    # -----------------------------------------------------
    # DATEIENDUNGEN PRÜFEN
    # -----------------------------------------------------

    allowed_games = [
        ".html",
        ".htm",
        ".zip"
    ]

    allowed_images = [
        ".png",
        ".jpg",
        ".jpeg",
        ".webp"
    ]


    game_extension = os.path.splitext(
        game_filename
    )[1].lower()


    thumb_extension = os.path.splitext(
        thumb_filename
    )[1].lower()


    if game_extension not in allowed_games:

        return (
            "Nur HTML-, HTM- oder ZIP-Spiele "
            "sind erlaubt.",
            400
        )


    if thumb_extension not in allowed_images:

        return (
            "Das Thumbnail muss PNG, JPG, "
            "JPEG oder WEBP sein.",
            400
        )


    # -----------------------------------------------------
    # DATEIEN SPEICHERN
    # -----------------------------------------------------

    game_path = os.path.join(
        GAME_FOLDER,
        game_filename
    )

    thumb_path = os.path.join(
        THUMB_FOLDER,
        thumb_filename
    )


    game_file.save(
        game_path
    )

    thumbnail.save(
        thumb_path
    )


    # -----------------------------------------------------
    # SPIELDATEN LADEN
    # -----------------------------------------------------

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            games = json.load(f)

    except Exception:

        games = []


    # -----------------------------------------------------
    # NEUES SPIEL
    # -----------------------------------------------------

    new_game = {

        "name": name,

        "genre": genre,

        "description": description,

        "game": game_filename,

        "thumbnail": thumb_filename

    }


    games.append(
        new_game
    )


    # -----------------------------------------------------
    # SPEICHERN
    # -----------------------------------------------------

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            games,
            f,
            ensure_ascii=False,
            indent=2
        )


    return redirect(
        url_for("home")
    )


# =========================================================
# THUMBNAILS
# =========================================================

@app.route(
    "/uploads/thumbnails/<filename>"
)
def thumbnail(filename):

    from flask import send_from_directory

    return send_from_directory(
        THUMB_FOLDER,
        filename
    )


# =========================================================
# SPIELDATEIEN
# =========================================================

@app.route(
    "/uploads/games/<filename>"
)
def game_file(filename):

    from flask import send_from_directory

    return send_from_directory(
        GAME_FOLDER,
        filename
    )


# =========================================================
# GOOGLE LOGIN
# =========================================================

@app.route("/auth/google")
def google_login():

    # Google OAuth wird später hier angeschlossen.
    # Dafür brauchen wir eine Google Client ID
    # und ein Google Client Secret.

    return """
    <html>
    <head>
        <title>Google Login</title>
        <meta charset="UTF-8">
        <style>
            body {
                background:#07111f;
                color:white;
                font-family:Arial;
                text-align:center;
                padding-top:100px;
            }

            a {
                color:#60a5fa;
                text-decoration:none;
            }
        </style>
    </head>

    <body>

        <h1>Google Anmeldung</h1>

        <p>
            Die Google-Anmeldung wird gerade eingerichtet.
        </p>

        <a href="/">
            ← Zurück zu SliqGames
        </a>

    </body>
    </html>
    """


# =========================================================
# SERVER START
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )