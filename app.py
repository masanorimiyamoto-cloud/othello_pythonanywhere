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
# 盤面操作用ユーティリティ
DIRECTIONS = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]

def inside_board(r: int, c: int) -> bool:
    return 0 <= r < 8 and 0 <= c < 8

def stones_to_flip(board: List[List[int]], row: int, col: int, turn: int) -> List[tuple]:
    """
    (row,col) に turn の石を置いたときに返せる相手石のリストを返す。
    返せる石がない場合は空リスト。
    """
    flips = []
    for dr, dc in DIRECTIONS:
        path = []
        r, c = row + dr, col + dc
        # まず隣が相手石であること
        while inside_board(r, c) and board[r][c] == -turn:
            path.append((r, c))
            r += dr
            c += dc
        # 最後に自分の石があれば path を flips に追加
        if inside_board(r, c) and board[r][c] == turn and path:
            flips.extend(path)
    return flips

def has_valid_move(board: List[List[int]], turn: int) -> bool:
    """turn の合法手が1つでもあれば True"""
    for r in range(8):
        for c in range(8):
            if board[r][c] == 0 and stones_to_flip(board, r, c, turn):
                return True
    return False

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
    data = request.get_json()
    row, col = int(data["row"]), int(data["col"])
    board = session.get("board", init_board())
    turn = session.get("turn", -1)

    # 既に石がある or 合法手でない
    if board[row][col] != 0:
        return jsonify({"status": "cell occupied"}), 400

    flips = stones_to_flip(board, row, col, turn)
    if not flips:
        return jsonify({"status": "invalid move"}), 400

    # 石を配置 & 返す
    board[row][col] = turn
    for r, c in flips:
        board[r][c] = turn

    # 次の手番
    next_turn = -turn
    # 次のプレイヤーに合法手がなければパス
    if not has_valid_move(board, next_turn):
        # 両者パス → ゲーム終了
        if not has_valid_move(board, turn):
            # 終了フラグを返してクライアント側で勝敗表示
            session["game_over"] = True
            # スコア計算
            white = sum(cell==1 for row in board for cell in row)
            black = sum(cell==-1 for row in board for cell in row)
            session["score"] = {"white": white, "black": black}
            session["board"] = board
            return jsonify({
                "status": "game_over",
                "board": board,
                "score": session["score"]
            })
        # 片方だけパス
        next_turn = turn  # 手番戻す
        passed = True
    else:
        passed = False

    session["board"] = board
    session["turn"] = next_turn
    return jsonify({
        "status": "success",
        "board": board,
        "turn": next_turn,
        "passed": passed
    })



if __name__ == "__main__":
    app.run(debug=True)
