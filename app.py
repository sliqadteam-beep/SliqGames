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

@app.route("/archer-hero")
def archer_hero():
    return """
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Archer Hero - SliqGames</title>

<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #07111f;
    color: white;
    font-family: Arial, sans-serif;
    overflow: hidden;
}

.top {
    height: 65px;
    background: #0b1829;
    border-bottom: 1px solid #243952;
    display: flex;
    align-items: center;
    padding: 0 20px;
}

.back {
    background: #2563eb;
    border: 0;
    color: white;
    padding: 11px 18px;
    border-radius: 10px;
    cursor: pointer;
    font-weight: bold;
}

.title {
    margin-left: 18px;
    font-size: 20px;
    font-weight: bold;
}

.game {
    height: calc(100vh - 65px);
    display: flex;
    align-items: center;
    justify-content: center;
}

canvas {
    background: #102b52;
    border: 2px solid #3b82f6;
    border-radius: 15px;
    max-width: 95vw;
    max-height: 85vh;
}
</style>
</head>

<body>

<div class="top">

<button class="back" onclick="window.location.href='/'">
← SliqGames
</button>

<div class="title">
🏹 Archer Hero
</div>

</div>

<div class="game">

<canvas id="canvas" width="900" height="550"></canvas>

</div>

<script>

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

let player = {
    x: 100,
    y: 450,
    width: 40,
    height: 60
};

let enemy = {
    x: 700,
    y: 430,
    width: 45,
    height: 70,
    health: 100
};

let arrows = [];

let keys = {};

document.addEventListener("keydown", function(e) {
    keys[e.key.toLowerCase()] = true;
});

document.addEventListener("keyup", function(e) {
    keys[e.key.toLowerCase()] = false;
});

canvas.addEventListener("click", function(e) {

    const rect = canvas.getBoundingClientRect();

    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const angle = Math.atan2(
        mouseY - player.y,
        mouseX - player.x
    );

    arrows.push({
        x: player.x + 25,
        y: player.y + 20,
        vx: Math.cos(angle) * 10,
        vy: Math.sin(angle) * 10
    });

});

function update() {

    if (keys["a"] || keys["arrowleft"]) {
        player.x -= 5;
    }

    if (keys["d"] || keys["arrowright"]) {
        player.x += 5;
    }

    if (keys["w"] || keys["arrowup"]) {
        player.y -= 5;
    }

    if (keys["s"] || keys["arrowdown"]) {
        player.y += 5;
    }

    player.x = Math.max(20, Math.min(canvas.width - 60, player.x));
    player.y = Math.max(50, Math.min(canvas.height - 80, player.y));

    arrows.forEach(arrow => {

        arrow.x += arrow.vx;
        arrow.y += arrow.vy;

        if (
            arrow.x > enemy.x &&
            arrow.x < enemy.x + enemy.width &&
            arrow.y > enemy.y &&
            arrow.y < enemy.y + enemy.height
        ) {

            enemy.health -= 20;

            arrow.x = -100;

            if (enemy.health <= 0) {
                enemy.health = 100;
                enemy.x = 600 + Math.random() * 200;
                alert("🏆 Gegner besiegt!");
            }

        }

    });

    arrows = arrows.filter(
        arrow =>
        arrow.x > 0 &&
        arrow.x < canvas.width &&
        arrow.y > 0 &&
        arrow.y < canvas.height
    );

}

function draw() {

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Boden
    ctx.fillStyle = "#17395c";
    ctx.fillRect(0, 500, canvas.width, 50);

    // Spieler
    ctx.fillStyle = "#60a5fa";
    ctx.fillRect(
        player.x,
        player.y,
        player.width,
        player.height
    );

    // Bogen
    ctx.strokeStyle = "#facc15";
    ctx.lineWidth = 5;

    ctx.beginPath();
    ctx.arc(
        player.x + 40,
        player.y + 25,
        25,
        -Math.PI / 2,
        Math.PI / 2
    );
    ctx.stroke();

    // Gegner
    ctx.fillStyle = "#ef4444";

    ctx.fillRect(
        enemy.x,
        enemy.y,
        enemy.width,
        enemy.height
    );

    // Gegner-Leben
    ctx.fillStyle = "#111827";
    ctx.fillRect(
        enemy.x,
        enemy.y - 15,
        45,
        7
    );

    ctx.fillStyle = "#22c55e";
    ctx.fillRect(
        enemy.x,
        enemy.y - 15,
        45 * (enemy.health / 100),
        7
    );

    // Pfeile
    ctx.strokeStyle = "#facc15";
    ctx.lineWidth = 4;

    arrows.forEach(arrow => {

        ctx.beginPath();

        ctx.moveTo(
            arrow.x,
            arrow.y
        );

        ctx.lineTo(
            arrow.x - arrow.vx * 0.5,
            arrow.y - arrow.vy * 0.5
        );

        ctx.stroke();

    });

    ctx.fillStyle = "white";
    ctx.font = "18px Arial";

    ctx.fillText(
        "WASD / Pfeiltasten = Bewegen",
        20,
        30
    );

    ctx.fillText(
        "Klicke zum Schießen",
        20,
        52
    );

}

function loop() {

    update();
    draw();

    requestAnimationFrame(loop);

}

loop();

</script>

</body>
</html>
"""

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

    game_file.save(
        os.path.join(GAME_FOLDER, game_filename)
    )

    thumbnail.save(
        os.path.join(THUMB_FOLDER, thumb_filename)
    )

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        games = json.load(f)

    games.append({
        "name": name,
        "genre": genre,
        "description": description,
        "game": game_filename,
        "thumbnail": thumb_filename
    })

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            games,
            f,
            ensure_ascii=False,
            indent=2
        )

    return redirect(url_for("home"))

@app.route("/games.json")
def games_json():

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        games = json.load(f)

    return games

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


@app.route('/racing')
def racing():
    return render_template('racing.html')

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )


