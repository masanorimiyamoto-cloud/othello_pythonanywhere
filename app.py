from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
from game_manager import GameManager
import os
# app.py の中
from othello_ai import OthelloAI

ai_player_id = "AI"
ai = OthelloAI(max_depth=3)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key")
socketio = SocketIO(app)

# ゲームマネージャーの初期化
game_manager = GameManager()

@app.route("/")
def index():
    return render_template("othello.html")

@app.route("/create_room")
def create_room():
    game_id = game_manager.create_game()
    return {"game_id": game_id}

@socketio.on("connect")
def handle_connect():
    emit("connection_established", {"message": "Connected"})

@socketio.on("join_game")
def handle_join_game(data):
    game_id   = data["game_id"]
    player_id = data["player_id"]
    name      = data.get("name", "Player")
    if data.get("mode") == "single":  # シングルプレイ指定なら
        game_manager.add_player(game_id, ai_player_id, name="Computer")

    game_data = game_manager.get_game(game_id)
    if not game_data:
        emit("error", {"message": "Game not found"})
        return

    if not game_manager.add_player(game_id, player_id, name):
        emit("error", {"message": "Game is full"})
        return

    join_room(game_id)

    # プレイヤーリスト＆自分の色
    players = game_data["players"]
    idx = next(i for i,p in enumerate(players) if p.id == player_id)
    color = -1 if idx == 0 else 1

    # 参加成功イベント
    emit("joined", {
        "players":     [{"id": p.id, "name": p.name} for p in players],
        "your_color":  color,
        "board":       game_data["game"].board,
        "turn":        game_data["game"].turn
    })

    # 全員に初期状態をブロードキャスト
    emit("game_state", {
        "board":     game_data["game"].board,
        "turn":      game_data["game"].turn,
        "players":   [{"id": p.id, "name": p.name} for p in players]
    }, room=game_id)


@socketio.on("make_move")
def handle_move(data):
    game_id   = data.get("game_id")
    player_id = data.get("player_id")
    row, col  = data.get("row"), data.get("col")

    game_data = game_manager.get_game(game_id)
    if not game_data:
        emit("error", {"message": "Game not found"})
        return

    players = game_data["players"]
    try:
        player_index = next(i for i,p in enumerate(players) if p.id == player_id)
    except StopIteration:
        emit("error", {"message": "Player not in game"})
        return

    expected_turn = -1 if player_index == 0 else 1
    # デバッグログ（必要に応じてコメントアウトしてください）
    

    if game_data["game"].turn != expected_turn:
        emit("error", {"message": "Not your turn"})
        return

    result = game_data["game"].make_move(row, col)
    # もし次のターンが AI の番なら
    if game_data["game"].turn == 1 and ai_player_id in [p.id for p in game_data["players"]]:
        # AI が手を選ぶ
        r, c = ai.choose_move(game_data["game"])
        result = game_data["game"].make_move(r, c)
        # ブロードキャスト
        emit("game_state", {
            "board": game_data["game"].board,
            "turn":  game_data["game"].turn,
            "last_move": [r, c]
        }, room=game_id)
    # 無効手は弾く
    if result["status"] in ("cell occupied", "invalid move"):
        emit("error", {"message": result.get("message", "Invalid move")})
        return

    # 成功 or 終了 の両方で更新を送信
    payload = {
        "board":     game_data["game"].board,
        "turn":      game_data["game"].turn,
        "last_move": [row, col]
    }
    if result["status"] == "game_over":
        payload["status"] = "game_over"
        payload["score"]  = result["score"]

    emit("game_state", payload, room=game_id)


if __name__ == "__main__":
    socketio.run(app, debug=True)
