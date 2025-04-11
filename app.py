import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit
from game_manager import GameManager
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key")
socketio = SocketIO(app)

# ゲームマネージャーの初期化
game_manager = GameManager()

@app.route("/")
def index():
    """ゲームルーム作成ページ"""
    return render_template("othello.html")

@app.route("/create_room")
def create_room():
    """新しいゲームルームを作成"""
    game_id = game_manager.create_game()
    return {"game_id": game_id}

# WebSocketイベントハンドラ
@socketio.on("connect")
def handle_connect():
    """クライアント接続時"""
    emit("connection_established", {"message": "Connected"})

from flask_socketio import join_room, emit

from flask_socketio import join_room, emit

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

    # プレイヤーリスト
    players = game_data["players"]
    # 自分のインデックスを取得
    idx = next(i for i,p in enumerate(players) if p.id == player_id)
    # 先着0番が黒(-1)、1番が白(1)
    color = -1 if idx == 0 else 1

    # 参加成功＋自分の色を通知
    emit("joined", {
        "players": [{"id": p.id, "name": p.name} for p in players],
        "your_color": color,
        "board":  game_data["game"].board,
        "turn":   game_data["game"].turn
    })
    
    # 全員に現在の状態を更新（既存コードの game_state 送信）
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

    # ① プレイヤーリストから送信者のインデックス（0 or 1）を探す
    players = game_data["players"]
    try:
        player_index = next(i for i,p in enumerate(players) if p.id == player_id)
    except StopIteration:
        emit("error", {"message": "Player not in game"})
        return

    # ② game.turn との照合
    #    例: game.turn == -1 が黒、1 が白、player_index 0 を黒、1 を白 と割り当てる場合
    expected_turn = -1 if player_index == 0 else 1
    if game_data["game"].turn != expected_turn:
        emit("error", {"message": "Not your turn"})
        return

    # ③ 合法手チェックは OthelloGame.make_move に任せつつ
    result = game_data["game"].make_move(row, col)
    if result["status"] != "success":
        emit("error", {"message": result.get("message", "Invalid move")})
        return

    # ④ 成功時に全員へ更新を送信
    emit("game_state", {
        "board":     game_data["game"].board,
        "turn":      game_data["game"].turn,
        "last_move": [row, col]
    }, room=game_id)

if __name__ == "__main__":
    socketio.run(app, debug=True)