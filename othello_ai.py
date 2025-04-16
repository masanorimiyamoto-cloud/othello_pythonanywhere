# othello_ai.py
from othello import OthelloGame
import math

class OthelloAI:
    LEVEL_DEPTH = {
        3: 3,
        4: 5,
        5: 7,
    }

    def __init__(self, level=4):
        # レベルから深度を決定。存在しなければデフォルト4
        self.max_depth = self.LEVEL_DEPTH.get(level, 4)
        

    def evaluate(self, board):
        # 単純に石の差を評価
        white = sum(cell == 1 for row in board for cell in row)
        black = sum(cell == -1 for row in board for cell in row)
        return white - black

    def minimax(self, game: OthelloGame, depth, alpha, beta, maximizing_player):
        if depth == 0 or not game.has_valid_move(game.turn):
            return self.evaluate(game.board), None

        best_move = None
        if maximizing_player:
            max_eval = -math.inf
            for r in range(8):
                for c in range(8):
                    if game.board[r][c] == 0:
                        flips = game.stones_to_flip(r, c, game.turn)
                        if not flips: continue
                        # コピーして手を打つ
                        clone = OthelloGame()
                        clone.board = [row[:] for row in game.board]
                        clone.turn = game.turn
                        clone.make_move(r, c)
                        eval_score, _ = self.minimax(clone, depth-1, alpha, beta, False)
                        if eval_score > max_eval:
                            max_eval, best_move = eval_score, (r, c)
                        alpha = max(alpha, eval_score)
                        if beta <= alpha:
                            break
            return max_eval, best_move
        else:
            min_eval = math.inf
            for r in range(8):
                for c in range(8):
                    if game.board[r][c] == 0:
                        flips = game.stones_to_flip(r, c, game.turn)
                        if not flips: continue
                        clone = OthelloGame()
                        clone.board = [row[:] for row in game.board]
                        clone.turn = game.turn
                        clone.make_move(r, c)
                        eval_score, _ = self.minimax(clone, depth-1, alpha, beta, True)
                        if eval_score < min_eval:
                            min_eval, best_move = eval_score, (r, c)
                        beta = min(beta, eval_score)
                        if beta <= alpha:
                            break
            return min_eval, best_move

    def choose_move(self, game: OthelloGame):
        _, move = self.minimax(game, self.max_depth, -math.inf, math.inf, True)
        return move
