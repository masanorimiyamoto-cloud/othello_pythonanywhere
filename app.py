from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
import os
import time

from game_manager import GameManager
from othello_ai import OthelloAI
from othello import OthelloGame

# -----------------------------------------------------------------------------
# App & SocketIO Initialization
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
socketio = SocketIO(app)

# -----------------------------------------------------------------------------
# Game Manager & Constants
# -----------------------------------------------------------------------------
game_manager = GameManager()
AI_PLAYER_ID = "AI"
# Human move delay parameters
BASE_DELAY    = 0.5   # seconds
PER_FLIP_SEC  = 0.1   # additional seconds per flipped stone

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("othello.html")

@app.route("/create_room")
def create_room():
    game_id = game_manager.create_game()
    return {"game_id": game_id}

# -----------------------------------------------------------------------------
# Socket.IO Events: Connection
# -----------------------------------------------------------------------------
@socketio.on("connect")
def handle_connect():
    emit("connection_established", {"message": "Connected"})

# -----------------------------------------------------------------------------
# Socket.IO Events: AI Game Start
# -----------------------------------------------------------------------------
@socketio.on("start_ai_game")
def on_start_ai(data):
    level = data.get("level", 4)
    game_id = data.get("game_id")
    client_player_id = data.get("player_id")

    if not game_id:
        game_id = game_manager.create_game()
        emit("room_created", {"game_id": game_id})

    join_room(game_id)
    game_data = game_manager.get_game(game_id)
    if not game_data:
        emit("error", {"message": "Game not found"})
        return

    # Reset players
    game_data["players"] = []
    # Add human (Black)
    game_manager.add_player(game_id, client_player_id, name="Human")
    # Add AI (White)
    ai = OthelloAI(level=level)
    game_data["ai"] = ai
    game_manager.add_player(game_id, AI_PLAYER_ID, name="Computer")
    # Start with Black
    game_data["game"].turn = -1

    emit("joined", {
        "game_id": game_id,
        "players": [{"id": p.id, "name": p.name} for p in game_data["players"]],
        "your_color": -1,
        "board": game_data["game"].board,
        "turn": game_data["game"].turn
    }, room=game_id)

    emit("game_state", {
        "board": game_data["game"].board,
        "turn": game_data["game"].turn,
        "players": [{"id": p.id, "name": p.name} for p in game_data["players"]],
        "your_color": -1
    }, room=game_id)

# -----------------------------------------------------------------------------
# Socket.IO Events: Join Game
# -----------------------------------------------------------------------------
@socketio.on("join_game")
def handle_join_game(data):
    game_id   = data["game_id"]
    player_id = data["player_id"]
    name      = data.get("name", "Player")

    game_data = game_manager.get_game(game_id)
    if not game_data:
        emit("error", {"message": "Game not found"})
        return

    if not game_manager.add_player(game_id, player_id, name):
        emit("error", {"message": "Game is full"})
        return

    join_room(game_id)
    players = game_data["players"]
    idx = next(i for i, p in enumerate(players) if p.id == player_id)
    color = -1 if idx == 0 else 1

    emit("joined", {
        "players":    [{"id": p.id, "name": p.name} for p in players],
        "your_color": color,
        "board":      game_data["game"].board,
        "turn":       game_data["game"].turn
    })

    emit("game_state", {
        "board":   game_data["game"].board,
        "turn":    game_data["game"].turn,
        "players": [{"id": p.id, "name": p.name} for p in players]
    }, room=game_id)

# -----------------------------------------------------------------------------
# Socket.IO Events: Move Handling
# -----------------------------------------------------------------------------
@socketio.on("make_move")
def handle_move(data):
    game_id    = data.get("game_id")
    player_id  = data.get("player_id")
    row, col   = data.get("row"), data.get("col")

    game_data = game_manager.get_game(game_id)
    if not game_data:
        emit("error", {"message": "Game not found"})
        return

    try:
        player_index = next(i for i, p in enumerate(game_data["players"]) if p.id == player_id)
    except StopIteration:
        emit("error", {"message": "Player not in game"})
        return

    expected_turn = -1 if player_index == 0 else 1
    if game_data["game"].turn != expected_turn:
        emit("error", {"message": f"Not your turn (Expected:{expected_turn}, Actual:{game_data['game'].turn})"})
        return

    # 1) Black (Human) flips count
    flips = game_data["game"].stones_to_flip(row, col, game_data["game"].turn)
    num_flips = len(flips)

    # 2) Apply human move
    result = game_data["game"].make_move(row, col)
    if result["status"] in ("cell occupied", "invalid move"):
        emit("error", {"message": result.get("message", "Invalid move")})
        return

    # 3) Send human move state
    human_move_payload = {
        "board": game_data["game"].board,
        "turn": game_data["game"].turn,
        "last_move": [row, col],
        "status": "ongoing",
        "player_move": True
    }
    if result["status"] == "game_over":
        human_move_payload.update({
            "status": "game_over",
            "score": {
                "white": int(result["score"]["white"]),
                "black": int(result["score"]["black"])
            }
        })
    emit("game_state", human_move_payload, room=game_id)

    # 4) Delay before AI move based on flips
    delay = BASE_DELAY + PER_FLIP_SEC * num_flips
    time.sleep(delay)

    # 5) AI move
    ai = game_data.get("ai")
    if ai and human_move_payload["status"] == "ongoing" and game_data["game"].turn == 1 and game_data["game"].has_valid_move(1):
        emit("ai_thinking", {}, room=game_id)
        r, c = ai.choose_move(game_data["game"])
        ai_result = game_data["game"].make_move(r, c)

        ai_move_payload = {
            "board": game_data["game"].board,
            "turn": game_data["game"].turn,
            "last_move": [r, c],
            "status": "ongoing",
            "ai_move": True
        }
        if ai_result["status"] == "game_over":
            ai_move_payload.update({
                "status": "game_over",
                "score": {
                    "white": int(ai_result["score"]["white"]),
                    "black": int(ai_result["score"]["black"])
                }
            })
        emit("game_state", ai_move_payload, room=game_id)

# -----------------------------------------------------------------------------
# Main Entry
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    socketio.run(app, debug=True)
