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
BASE_DELAY    = 1.0   # seconds
PER_FLIP_SEC  = 0.1   # additional seconds per flipped stone

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("othello.html")

# -----------------------------------------------------------------------------
# Socket.IO Events: Connection
# -----------------------------------------------------------------------------
@socketio.on("connect")
def handle_connect():
    emit("connection_established", {"message": "Connected"})

# -----------------------------------------------------------------------------
# Socket.IO Events: Room Management
# -----------------------------------------------------------------------------
@socketio.on("create_room")
def handle_create_room(data):
    """Socket.IOでルーム作成を処理"""
    game_id = game_manager.create_game()
    join_room(game_id)
    emit("room_created", {"game_id": game_id}, room=request.sid)

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
        emit("room_created", {"game_id": game_id}, room=request.sid)

    join_room(game_id)
    game_data = game_manager.get_game(game_id)
    if not game_data:
        emit("error", {"message": "Game not found"}, room=request.sid)
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
    }, room=request.sid)

    emit("game_state", {
        "board": game_data["game"].board,
        "turn": game_data["game"].turn,
        "players": [{"id": p.id, "name": p.name} for p in game_data["players"]],
        "status": "ongoing"
    }, room=game_id)


# -----------------------------------------------------------------------------
# Socket.IO Events: Join Game
@socketio.on("join_game")
def handle_join_game(data):
    print(f"\n=== JOIN GAME REQUEST ===")  # デバッグ開始
    print(f"Received data: {data}")  # 受信データ表示
    
    game_id = data["game_id"]
    player_id = data["player_id"]
    name = data.get("name", "Player")

    print(f"Attempting to join game: {game_id} as player: {player_id}")

    game_data = game_manager.get_game(game_id)
    if not game_data:
        error_msg = f"Game not found: {game_id}"
        print(error_msg)
        emit("error", {"message": error_msg}, room=request.sid)
        return

    print(f"Current players in game: {[p.id for p in game_data['players']]}")

    # 既存プレイヤーチェック
    existing_player = next((p for p in game_data["players"] if p.id == player_id), None)
    if existing_player:
        print(f"Player already in game: {player_id}")
        color = -1 if game_data["players"][0].id == player_id else 1
    else:
        if not game_manager.add_player(game_id, player_id, name):
            error_msg = f"Game is full: {game_id}"
            print(error_msg)
            emit("error", {"message": error_msg}, room=request.sid)
            return
        color = -1 if len(game_data["players"]) == 1 else 1
        print(f"Added new player: {player_id} as {'Black' if color == -1 else 'White'}")

    join_room(game_id)
    print(f"Player {player_id} joined room: {game_id}")

    players = game_data["players"]
    print(f"Current player count: {len(players)}")

    # 参加者に送信
    join_payload = {
        "game_id": game_id,
        "players": [{"id": p.id, "name": p.name} for p in players],
        "your_color": color,
        "board": game_data["game"].board,
        "turn": game_data["game"].turn
    }
    print(f"Sending 'joined' event to player: {join_payload}")
    emit("joined", join_payload, room=request.sid)

    # 全員にブロードキャスト
    state_payload = {
        "board": game_data["game"].board,
        "turn": game_data["game"].turn,
        "players": [{"id": p.id, "name": p.name} for p in players],
        "status": "ongoing"
    }
    print(f"Broadcasting 'game_state' to room: {state_payload}")
    emit("game_state", state_payload, room=game_id)

    # 2人揃ったらゲーム開始
    if len(players) == 2 and not game_data.get("ai"):
        print("Two players joined - starting game")
        emit("game_started", {
            "game_id": game_id,
            "board": game_data["game"].board,
            "turn": -1,
            "players": [{"id": p.id, "name": p.name} for p in players]
        }, room=game_id)

    print("=== JOIN GAME COMPLETE ===\n")

    

# ─────────────────────────────────────────────────────────────────────────────
# Socket.IO Events: Move Handling
# ─────────────────────────────────────────────────────────────────────────────
@socketio.on("make_move")
def handle_move(data):
    game_id   = data.get("game_id")
    player_id = data.get("player_id")
    row, col  = data.get("row"), data.get("col")

    game_data = game_manager.get_game(game_id)
    # … your existing validation here …

    # 1) Apply the human move and broadcast immediately
    
    result = game_data["game"].make_move(row, col)
    human_payload = {
        "board":      game_data["game"].board,
        "turn":       game_data["game"].turn,
        "last_move":  [row, col],
        "status":     result["status"],
        "players":    [{"id": p.id, "name": p.name} for p in game_data["players"]]
    }
    emit("game_state", human_payload, room=game_id)

    # 2) If it’s an AI game and not over, schedule the AI move in background
    if "ai" in game_data and result["status"] != "game_over" and game_data["game"].turn == 1:
        # start background task so this handler returns immediately
        socketio.start_background_task(run_ai_move, game_id)


def run_ai_move(game_id):
    """Background task: pick, delay, and emit the AI’s white move."""
    game_data = game_manager.get_game(game_id)
    if not game_data:
        return

    # A) notify clients that AI is thinking
    socketio.emit("ai_thinking", {}, room=game_id)

    # B) 変更点1: 変更前の盤面をディープコピー
    before = [row[:] for row in game_data["game"].board]
    
    # pick & apply the AI’s move
    r, c   = game_data["ai"].choose_move(game_data["game"])
    ai_res = game_data["game"].make_move(r, c)
    after  = game_data["game"].board
    
    # 変更点2: 反転した石と新しい石を検出
    flips = []
    new_stone = None
    for y in range(8):
        for x in range(8):
            # 新しい石の検出 (0 → 1)
            if before[y][x] == 0 and after[y][x] == 1:
                new_stone = {"y": y, "x": x}
            # 反転した石の検出 (-1 → 1)
            elif before[y][x] == -1 and after[y][x] == 1:
                flips.append({"y": y, "x": x})

    # C) delay proportional to human flips
    delay = BASE_DELAY + PER_FLIP_SEC * len(flips)
    time.sleep(delay)

    # D) 変更点3: 新しい石と反転情報を追加
    ai_payload = {
        "board":      after,
        "turn":       game_data["game"].turn,
        "last_move":  [r, c],
        "status":     ai_res["status"],
        "players":    [{"id": p.id, "name": p.name} for p in game_data["players"]],
        "new_stone":  new_stone,  # 新しい石の位置
        "flips":      flips       # 反転した石のリスト
    }
    
    if ai_res["status"] == "game_over":
        ai_payload["score"] = {
            "white": int(ai_res["score"]["white"]),
            "black": int(ai_res["score"]["black"])
        }

    socketio.emit("ai_move", ai_payload, room=game_id)




# -----------------------------------------------------------------------------
# Main Entry
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    socketio.run(app, debug=True)