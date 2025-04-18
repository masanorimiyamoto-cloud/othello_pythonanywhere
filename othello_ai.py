from othello import OthelloGame
import math

class OthelloAI:
    LEVEL_DEPTH = { 3: 2, 4: 3, 5: 5 }

    def __init__(self, level=4):
        self.max_depth = self.LEVEL_DEPTH.get(level, 4)
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

    def evaluate(self, game: OthelloGame) -> float:
        board = game.board
        white_count = black_count = 0
        position_score = 0

        # 1) 石数カウント ＆ 位置評価
        for r in range(8):
            for c in range(8):
                cell = board[r][c]
                if cell == 1:
                    white_count += 1
                    position_score += self.value_table[r][c]
                elif cell == -1:
                    black_count += 1
                    position_score -= self.value_table[r][c]

        stone_count = white_count + black_count
        stone_diff  = white_count - black_count

        # 2) モビリティ（合法手の数の差）
        my_moves = len(game.valid_moves(1))
        op_moves = len(game.valid_moves(-1))
        mobility_score = my_moves - op_moves

        # 3) コーナー占拠
        corners = [(0,0),(0,7),(7,0),(7,7)]
        corner_score = 0
        for r, c in corners:
            if board[r][c] == 1:
                corner_score += 100
            elif board[r][c] == -1:
                corner_score -= 100

        # 4) フロンティア石（空セルに隣接する石へのペナルティ）
        dirs = [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
        frontier_penalty = 0
        for r in range(8):
            for c in range(8):
                if board[r][c] == 0:
                    continue
                for dr, dc in dirs:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < 8 and 0 <= nc < 8 and board[nr][nc] == 0:
                        frontier_penalty += -1 if board[r][c] == 1 else +1
                        break

        # 5) 動的重み付け
        if stone_count < 20:       # 序盤
            w_pos, w_mob, w_cor, w_fro, w_diff = 2.5,  5.0, 50.0, 1.0, 1.0
        elif stone_count < 50:     # 中盤
            w_pos, w_mob, w_cor, w_fro, w_diff = 2.0,  4.0, 60.0, 0.5, 2.0
        else:                      # 終盤
            w_pos, w_mob, w_cor, w_fro, w_diff = 1.0,  2.0, 80.0, 0.1, 5.0

        # 総合スコア
        score = (
            position_score * w_pos +
            mobility_score  * w_mob +
            corner_score    * w_cor +
            frontier_penalty* w_fro +
            stone_diff      * w_diff
        )
        return score

    def minimax(self, game: OthelloGame, depth, alpha, beta, maximizing_player):
        if depth == 0 or not game.has_valid_move(game.turn):
            return self.evaluate(game), None

        best_move = None
        if maximizing_player:
            max_eval = -math.inf
            for r in range(8):
                for c in range(8):
                    if game.board[r][c] != 0:
                        continue
                    if not game.stones_to_flip(r, c, game.turn):
                        continue
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
                    if game.board[r][c] != 0:
                        continue
                    if not game.stones_to_flip(r, c, game.turn):
                        continue
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
