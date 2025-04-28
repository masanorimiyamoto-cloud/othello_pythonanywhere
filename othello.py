from typing import List, Tuple, Dict

class OthelloGame:
    DIRECTIONS = [(-1, -1), (-1, 0), (-1, 1),
                  (0, -1),          (0, 1),
                  (1, -1),  (1, 0),  (1, 1)]
    
    def __init__(self):
        self.board = self.init_board()
        self.turn = -1  # 初期は黒

    @staticmethod
    def init_board() -> List[List[int]]:
        board = [[0]*8 for _ in range(8)]
        board[3][3] = board[4][4] = 1    # 白
        board[3][4] = board[4][3] = -1   # 黒
        return board

    @staticmethod
    def inside_board(r: int, c: int) -> bool:
        return 0 <= r < 8 and 0 <= c < 8
    def copy(self):
        """このゲーム状態のディープコピーを返す"""
        new_game = OthelloGame()
        # 盤面は行ごとにコピー
        new_game.board = [row[:] for row in self.board]
        # 手番もそのまま引き継ぎ
        new_game.turn = self.turn
        # もし他に持っている状態があればここでコピー
        # 例: new_game.history = self.history.copy()
        return new_game
    def stones_to_flip(self, row: int, col: int, turn: int) -> List[Tuple[int, int]]:
        flips = []
        for dr, dc in self.DIRECTIONS:
            path = []
            r, c = row + dr, col + dc
            while self.inside_board(r, c) and self.board[r][c] == -turn:
                path.append((r, c))
                r += dr
                c += dc
            if self.inside_board(r, c) and self.board[r][c] == turn and path:
                flips.extend(path)
        return flips

    def valid_moves(self, turn: int) -> List[Tuple[int, int]]:
        """指定色 turn の合法手を (row, col) のリストで返す"""
        return [(r, c) for r in range(8) for c in range(8)
               if self.board[r][c] == 0 and self.stones_to_flip(r, c, turn)]

    def has_valid_move(self, turn: int) -> bool:
        return len(self.valid_moves(turn)) > 0

    def check_game_over(self) -> bool:
        """ゲーム終了条件をチェック"""
        current_moves = self.has_valid_move(self.turn)
        next_moves = self.has_valid_move(-self.turn)
        return not current_moves and not next_moves

    def make_move(self, row: int, col: int) -> Dict:
        # 1) すでに埋まっているセル
        if self.board[row][col] != 0:
            return {"status": "cell occupied"}

        # 2) ひっくり返せる石を調べる
        flips = self.stones_to_flip(row, col, self.turn)
        if not flips:
            return {"status": "invalid move"}

        # 3) 石を置いて反転
        self.board[row][col] = self.turn
        for r, c in flips:
            self.board[r][c] = self.turn

        # 4) 全部置いたらゲーム終了チェック
        if self.check_game_over():
            white = sum(cell == 1 for row in self.board for cell in row)
            black = sum(cell == -1 for row in self.board for cell in row)
            return {
                "status": "game_over",
                "board": self.board,
                "score": {"white": white, "black": black}
            }

        # 5) 次のターン候補
        next_turn = -self.turn
        # パスが必要ならパスとして返す（self.turn はそのまま）
        if not self.has_valid_move(next_turn):
            return {
                "status": "pass",
                "board": self.board,
                "turn": self.turn
            }

        # 6) 正常にターンを更新
        self.turn = next_turn

        # 7) スコア計算（任意で付け加え）
        white = sum(cell == 1 for row in self.board for cell in row)
        black = sum(cell == -1 for row in self.board for cell in row)

        # 8) 正常終了レスポンス
        return {
            "status":      "success",
            "board":       self.board,
            "turn":        self.turn,
            "legal_moves": self.valid_moves(self.turn),
            "scores":      {"white": white, "black": black}
        }
