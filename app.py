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
    
    game_data = game_manager.get_game(game_id)
    if not game_data:
        emit("error", {"message": "Game not found"})
        return

    # まず、人間プレイヤーを追加
    if not game_manager.add_player(game_id, player_id, name):
        emit("error", {"message": "Game is full"})
        return

    # シングルプレイの場合のみ、次に AI を追加
    if data.get("mode") == "single":
        game_manager.add_player(game_id, ai_player_id, name="Computer")

    join_room(game_id)

    # プレイヤーリスト＆自分の色の決定
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
        "board":    game_data["game"].board,
        "turn":     game_data["game"].turn,
        "players":  [{"id": p.id, "name": p.name} for p in players]
    }, room=game_id)



@socketio.on("make_move")
def handle_move(data):
    game_id = data.get("game_id")
    player_id = data.get("player_id")
    row, col = data.get("row"), data.get("col")

    game_data = game_manager.get_game(game_id)
    if not game_data:
        emit("error", {"message": "Game not found"})
        return

    players = game_data["players"]
    try:
        player_index = next(i for i, p in enumerate(players) if p.id == player_id)
    except StopIteration:
        emit("error", {"message": "Player not in game"})
        return

    expected_turn = -1 if player_index == 0 else 1
    if game_data["game"].turn != expected_turn:
        emit("error", {"message": "Not your turn"})
        return

    result = game_data["game"].make_move(row, col)
    if result["status"] in ("cell occupied", "invalid move"):
        emit("error", {"message": result.get("message", "Invalid move")})
        return
    print(f"Player {player_id} (expected: {expected_turn}) is trying to move when turn is {game_data['game'].turn}")

    # ゲーム状態を送信
    payload = {
        "board": game_data["game"].board,
        "turn": game_data["game"].turn,
        "last_move": [row, col]
    }

    # ゲーム終了チェック
    if result["status"] == "game_over":
        payload["status"] = "game_over"
        payload["score"] = result["score"]
        emit("game_state", payload, room=game_id)
        return
 
    
    # ...（既存のコードはそのまま）

    # AIのターン処理（修正箇所）
    if (game_data["game"].turn == 1 and  # 白のターン（AI）か確認
        ai_player_id in [p.id for p in game_data["players"]] and
        game_data["game"].has_valid_moves()):
        
        try:
            r, c = ai.choose_move(game_data["game"])
            ai_result = game_data["game"].make_move(r, c)
            
            payload["board"] = game_data["game"].board
            payload["turn"] = game_data["game"].turn
            payload["last_move"] = [r, c]
            
            if ai_result["status"] == "game_over":
                payload["status"] = "game_over"
                payload["score"] = ai_result["score"]
            
        except Exception as e:
            print(f"AI move error: {e}")

    
    emit("game_state", payload, room=game_id)


if __name__ == "__main__":
    socketio.run(app, debug=True)
