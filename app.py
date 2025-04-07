from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
from datetime import datetime
import copy
import os
from typing import List

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key")

def init_board() -> List[List[int]]:
    """8x8の盤面を初期化。0: 空, 1: 白, -1: 黒"""
    board = [[0 for _ in range(8)] for _ in range(8)]
    board[3][3] = board[4][4] = 1    # 白
    board[3][4] = board[4][3] = -1   # 黒
    return board

@app.route("/")
def index():
    # セッションに盤面がなければ初期化
    if "board" not in session:
        session["board"] = init_board()
        # 現在の手番（1: 白、-1: 黒）
        session["turn"] = -1
    board = session.get("board")
    turn = session.get("turn")
    return render_template("othello.html", board=board, turn=turn)

@app.route("/reset", methods=["POST"])
def reset():
    session["board"] = init_board()
    session["turn"] = -1
    return jsonify({"status": "reset"})

@app.route("/move", methods=["POST"])
def move():
    try:
        data = request.get_json()
        row = int(data["row"])
        col = int(data["col"])
        if not (0 <= row < 8 and 0 <= col < 8):
            raise ValueError
        
        board = session.get("board", init_board())
        turn = session.get("turn", -1)
        
        if board[row][col] == 0:
            board[row][col] = turn
            session["board"] = board
            session["turn"] = -turn  # 手番交代
            return jsonify({"status": "success", "board": board, "turn": turn})
        else:
            return jsonify({"status": "cell occupied"}), 400
            
    except (KeyError, ValueError):
        return jsonify({"status": "invalid move"}), 400


if __name__ == "__main__":
    app.run(debug=True)
