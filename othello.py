# othello.py など別モジュールとして管理する例
from typing import List, Tuple

class OthelloGame:
    DIRECTIONS = [(-1, -1), (-1, 0), (-1, 1),
                  (0, -1),           (0, 1),
                  (1, -1),  (1, 0),  (1, 1)]
    
    def __init__(self):
        self.board = self.init_board()
        self.turn = -1  # 初期は黒

    @staticmethod
    def init_board() -> List[List[int]]:
        board = [[0 for _ in range(8)] for _ in range(8)]
        board[3][3] = board[4][4] = 1    # 白
        board[3][4] = board[4][3] = -1   # 黒
        return board

    @staticmethod
    def inside_board(r: int, c: int) -> bool:
        return 0 <= r < 8 and 0 <= c < 8

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

    def has_valid_move(self, turn: int) -> bool:
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == 0 and self.stones_to_flip(r, c, turn):
                    return True
        return False

    def make_move(self, row: int, col: int) -> dict:
        """
        手を打って盤面を更新する。
        戻り値は更新された情報（盤面・手番・パス状態など）をまとめた辞書。
        """
        if self.board[row][col] != 0:
            return {"status": "cell occupied"}

        flips = self.stones_to_flip(row, col, self.turn)
        if not flips:
            return {"status": "invalid move"}

        # 手を打った場所に石を置く
        self.board[row][col] = self.turn
        # ひっくり返す
        for r, c in flips:
            self.board[r][c] = self.turn

        next_turn = -self.turn
        passed = False
        if not self.has_valid_move(next_turn):
            # 次のプレイヤーに合法手がなければ，現プレイヤーが打てるかでゲーム終了かパスを決定
            if not self.has_valid_move(self.turn):
                # ゲーム終了
                white = sum(cell == 1 for row in self.board for cell in row)
                black = sum(cell == -1 for row in self.board for cell in row)
                return {"status": "game_over", "board": self.board,
                        "score": {"white": white, "black": black}}
            # パス処理の場合、手番は元に戻す
            next_turn = self.turn
            passed = True

        self.turn = next_turn
        return {"status": "success", "board": self.board, "turn": self.turn, "passed": passed}
