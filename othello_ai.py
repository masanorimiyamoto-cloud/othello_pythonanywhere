from othello import OthelloGame
import math

class OthelloAI:
    LEVEL_DEPTH = {
        3: 2,
        4: 3,
        5: 5,
    }

    def __init__(self, level=4):
        # レベルから深度を決定。存在しなければデフォルト4
        self.max_depth = self.LEVEL_DEPTH.get(level, 4)
        # 位置の価値テーブル
        self.value_table = [
            [100, -20, 10, 5, 5, 10, -20, 100],
            [-20, -50, -2, -2, -2, -2, -50, -20],
            [10, -2, 8, 0, 0, 8, -2, 10],
            [5, -2, 0, 1, 1, 0, -2, 5],
            [5, -2, 0, 1, 1, 0, -2, 5],
            [10, -2, 8, 0, 0, 8, -2, 10],
            [-20, -50, -2, -2, -2, -2, -50, -20],
            [100, -20, 10, 5, 5, 10, -20, 100]
        ]

    def evaluate(self, board):
        # 石数カウント
        stones_count = sum(1 for row in board for cell in row if cell != 0)
        white_count = sum(1 for row in board for cell in row if cell == 1)
        black_count = sum(1 for row in board for cell in row if cell == -1)
        stone_diff = white_count - black_count
        
        # 位置評価値
        position_score = 0
        for r in range(8):
            for c in range(8):
                if board[r][c] == 1:  # 白
                    position_score += self.value_table[r][c]
                elif board[r][c] == -1:  # 黒
                    position_score -= self.value_table[r][c]
        
        # ゲーム進行度による評価バランス調整
        if stones_count < 20:  # 序盤
            return position_score * 3 + stone_diff
        elif stones_count < 50:  # 中盤
            return position_score * 2 + stone_diff * 2
        else:  # 終盤
            return position_score + stone_diff * 5

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
