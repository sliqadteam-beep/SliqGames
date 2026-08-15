from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "sliqgames-development-key-change-this"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
GAME_FOLDER = os.path.join(UPLOAD_FOLDER, "games")
THUMB_FOLDER = os.path.join(UPLOAD_FOLDER, "thumbnails")

os.makedirs(GAME_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)

database_url = os.environ.get("DATABASE_URL")

if database_url:
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )
else:
    database_url = "sqlite:///" + os.path.join(BASE_DIR, "sliqgames.db")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

db = SQLAlchemy(app)


class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(32),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


class GameSave(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    game = db.Column(
        db.String(100),
        nullable=False
    )

    data = db.Column(
        db.Text,
        nullable=False,
        default="{}"
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "game",
            name="unique_user_game_save"
        ),
    )


class CommunityGame(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    genre = db.Column(
        db.String(50),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    game = db.Column(
        db.String(255),
        nullable=False
    )

    thumbnail = db.Column(
        db.String(255),
        nullable=False
    )

    creator = db.Column(
        db.String(32),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


with app.app_context():
    db.create_all()


@app.route("/")
def home():

    return render_template(
        "index.html",
        logged_in=("user_id" in session),
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

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    if len(username) < 3:
        return "Benutzername muss mindestens 3 Zeichen haben.", 400

    if len(username) > 32:
        return "Benutzername ist zu lang.", 400

    if len(password) < 6:
        return "Passwort muss mindestens 6 Zeichen haben.", 400

    existing = User.query.filter_by(
        username=username
    ).first()

    if existing:
        return "Dieser Benutzername ist bereits vergeben.", 400

    user = User(
        username=username,
        password_hash=generate_password_hash(password)
    )

    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    session["username"] = user.username

    return redirect(url_for("home"))


@app.route("/login", methods=["POST"])
def login():

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    user = User.query.filter_by(
        username=username
    ).first()

    if not user:
        return "Benutzername oder Passwort falsch.", 401

    if not check_password_hash(
        user.password_hash,
        password
    ):
        return "Benutzername oder Passwort falsch.", 401

    session["user_id"] = user.id
    session["username"] = user.username

    return redirect(url_for("home"))


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


@app.route("/api/account")
def account():

    if "user_id" not in session:
        return jsonify({
            "logged_in": False
        })

    user = User.query.get(session["user_id"])

    if not user:
        session.clear()

        return jsonify({
            "logged_in": False
        })

    return jsonify({
        "logged_in": True,
        "id": user.id,
        "username": user.username
    })


@app.route("/api/save/<game>", methods=["POST"])
def save_game(game):

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "error": "LOGIN_REQUIRED"
        }), 401

    if len(game) > 100:
        return jsonify({
            "success": False,
            "error": "INVALID_GAME"
        }), 400

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "INVALID_DATA"
        }), 400

    save = GameSave.query.filter_by(
        user_id=session["user_id"],
        game=game
    ).first()

    json_data = json.dumps(
        data,
        ensure_ascii=False
    )

    if save:

        save.data = json_data

    else:

        save = GameSave(
            user_id=session["user_id"],
            game=game,
            data=json_data
        )

        db.session.add(save)

    db.session.commit()

    return jsonify({
        "success": True
    })


@app.route("/api/save/<game>", methods=["GET"])
def load_game(game):

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "error": "LOGIN_REQUIRED"
        }), 401

    save = GameSave.query.filter_by(
        user_id=session["user_id"],
        game=game
    ).first()

    if not save:

        return jsonify({
            "success": True,
            "exists": False,
            "data": {}
        })

    try:
        data = json.loads(save.data)

    except:

        data = {}

    return jsonify({
        "success": True,
        "exists": True,
        "data": data
    })


@app.route("/api/save/<game>", methods=["DELETE"])
def delete_game_save(game):

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "error": "LOGIN_REQUIRED"
        }), 401

    save = GameSave.query.filter_by(
        user_id=session["user_id"],
        game=game
    ).first()

    if save:

        db.session.delete(save)
        db.session.commit()

    return jsonify({
        "success": True
    })


@app.route("/upload", methods=["POST"])
def upload_game():

    if "user_id" not in session:

        return "Du musst angemeldet sein, um ein Spiel hochzuladen.", 403

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

    game_file = request.files.get("game")
    thumbnail = request.files.get("thumbnail")

    if not name or not genre or not description:

        return "Bitte ALLE Felder ausfüllen!", 400

    if not game_file or not thumbnail:

        return "Spiel-Datei und Thumbnail werden benötigt.", 400

    game_filename = secure_filename(
        game_file.filename
    )

    thumb_filename = secure_filename(
        thumbnail.filename
    )

    if not game_filename or not thumb_filename:

        return "Ungültige Datei.", 400

    game_file.save(
        os.path.join(
            GAME_FOLDER,
            game_filename
        )
    )

    thumbnail.save(
        os.path.join(
            THUMB_FOLDER,
            thumb_filename
        )
    )

    community_game = CommunityGame(
        name=name,
        genre=genre,
        description=description,
        game=game_filename,
        thumbnail=thumb_filename,
        creator=session["username"]
    )

    db.session.add(community_game)
    db.session.commit()

    return redirect(url_for("home"))


@app.route("/games.json")
def games_json():

    games = CommunityGame.query.order_by(
        CommunityGame.created_at.desc()
    ).all()

    result = []

    for game in games:

        result.append({
            "id": game.id,
            "name": game.name,
            "genre": game.genre,
            "description": game.description,
            "game": game.game,
            "thumbnail": game.thumbnail,
            "creator": game.creator
        })

    return jsonify(result)


@app.route("/uploads/thumbnails/<filename>")
def thumbnail(filename):

    return send_from_directory(
        THUMB_FOLDER,
        filename
    )


@app.route("/uploads/games/<filename>")
def game_file(filename):

    return send_from_directory(
        GAME_FOLDER,
        filename
    )


@app.route("/api/health")
def health():

    return jsonify({
        "status": "online",
        "database": "connected"
    })


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
