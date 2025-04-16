
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room
from game_manager import GameManager
from othello_ai import OthelloAI
from othello import OthelloGame
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
socketio = SocketIO(app)

# ゲームマネージャーの初期化（ファイル冒頭で一度だけ）
game_manager = GameManager()
ai_player_id = "AI"

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
def start_singleplayer():
    # 新規部屋を作成
    game_id = game_manager.create_game()
    # ユーザーを追加
    player_id = "player-" + generate_unique_suffix()
    game_manager.add_player(game_id, player_id, name="Player")
    
    # AIの生成は on_start_ai で行うため、ここでは追加しない
    return {"game_id": game_id}

@socketio.on('start_ai_game')
def on_start_ai(data):
    level = data.get('level', 4)
    game_id = data.get('game_id')
    client_player_id = data.get('player_id')  # Get player_id from client
    
    if not game_id:
        game_id = game_manager.create_game()
        emit("room_created", {"game_id": game_id})

    join_room(game_id)
    
    game_data = game_manager.get_game(game_id)
    if not game_data:
        emit("error", {"message": "Game not found"})
        return

    # Add human player if not already added
    if not any(p.id == client_player_id for p in game_data["players"]):
        game_manager.add_player(game_id, client_player_id, name="Human")

    # Initialize AI if not already present
    if "ai" not in game_data:
        ai = OthelloAI(level=level)
        game_data["ai"] = ai
        game_manager.add_player(game_id, ai_player_id, name="Computer")

    # Determine player colors
    players = game_data["players"]
    human_player = next((p for p in players if p.id == client_player_id), None)
    if human_player:
        # Human is always Black (-1), AI is White (1)
        your_color = -1
    else:
        your_color = None

    emit('joined', {
        "game_id": game_id,
        "players": [{"id": p.id, "name": p.name} for p in players],
        "your_color": your_color,
        "board": game_data["game"].board,
        "turn": game_data["game"].turn
    }, room=game_id)

    emit('game_state', {
        "board": game_data["game"].board,
        "turn": game_data["game"].turn,
        "players": players,
        "your_color": your_color
    }, room=game_id)
    
@socketio.on("join_game")
def handle_join_game(data):
    game_id   = data["game_id"]
    player_id = data["player_id"]
    name      = data.get("name", "Player")

    game_data = game_manager.get_game(game_id)
    if not game_data:
        emit("error", {"message": "Game not found"})
        return

    # 人間プレイヤーを追加
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

    payload = {
        "board":     game_data["game"].board,
        "turn":      game_data["game"].turn,
        "last_move": [row, col]
    }
    print(f"Player {player_id} (expected_turn: {expected_turn}), actual turn: {game_data['game'].turn}")

    # ゲーム終了チェック
    if result["status"] == "game_over":
        payload["status"] = "game_over"
        payload["score"]  = result["score"]
        emit("game_state", payload, room=game_id)
        return

    # AIのターン処理
    ai = game_data.get("ai")
    if ai and game_data["game"].turn == 1 and game_data["game"].has_valid_move(1):
        r, c = ai.choose_move(game_data["game"])
        ai_result = game_data["game"].make_move(r, c)

        payload["board"]     = game_data["game"].board
        payload["turn"]      = game_data["game"].turn
        payload["last_move"] = [r, c]
        if ai_result["status"] == "game_over":
            payload["status"] = "game_over"
            payload["score"]  = ai_result["score"]

    emit("game_state", payload, room=game_id)

if __name__ == "__main__":
    socketio.run(app, debug=True)
