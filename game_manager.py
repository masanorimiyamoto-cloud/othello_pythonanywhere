import uuid
from typing import Dict, Optional
from othello import OthelloGame

class Player:
    def __init__(self, player_id: str, name: str = ""):
        self.id = player_id
        self.name = name

class GameManager:
    def __init__(self):
        self.games: Dict[str, dict] = {}  # {game_id: {"game": OthelloGame, "players": list[Player]}}
    
    def create_game(self) -> str:
        """新しいゲームを作成し、game_idを返す"""
        game_id = str(uuid.uuid4())
        self.games[game_id] = {
            "game": OthelloGame(),
            "players": []
        }
        return game_id
    def add_ai(self, game_id, ai: OthelloAI):
        self.games[game_id]["ai"] = ai
    def get_game(self, game_id: str) -> Optional[dict]:
        """game_idに対応するゲーム状態を取得"""
        return self.games.get(game_id)
    
    def add_player(self, game_id: str, player_id: str, name: str = "") -> bool:
        """ゲームにプレイヤーを参加させる"""
        game_data = self.get_game(game_id)
        if not game_data:
            return False
        
        if len(game_data["players"]) >= 2:
            return False  # 2人まで
        
        game_data["players"].append(Player(player_id, name))
        return True
    
    def remove_player(self, game_id: str, player_id: str):
        """プレイヤーをゲームから退出させる"""
        game_data = self.get_game(game_id)
        if game_data:
            game_data["players"] = [p for p in game_data["players"] if p.id != player_id]