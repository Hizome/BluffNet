from enum import Enum
from pydantic import BaseModel
from typing import List, Optional

class GameStage(str, Enum):
    PREFLOP = "PREFLOP"
    FLOP = "FLOP"
    TURN = "TURN"
    RIVER = "RIVER"
    SHOWDOWN = "SHOWDOWN"

class ActionType(str, Enum):
    FOLD = "FOLD"
    CHECK = "CHECK"
    CALL = "CALL"
    RAISE = "RAISE"
    ALL_IN = "ALL_IN"

class PlayerAction(BaseModel):
    type: ActionType
    amount: int = 0  # Only meaningful for RAISE

class Card(BaseModel):
    suit: str
    rank: str
    
    def __str__(self):
        return f"{self.rank}{self.suit}"

class Player(BaseModel):
    id: int
    name: str
    chips: int
    cards: List[Card] = []
    is_active: bool = True  # Not folded
    is_all_in: bool = False
    current_bet: int = 0  # Amount bet in current round
    position: int  # 0-7
    persona: str = "Default"
    thought: str = ""
    last_action: str = ""
    total_hand_bet: int = 0
    stats: dict = {"wins": 0, "hands_played": 0}

class Pot(BaseModel):
    amount: int
    eligible_players: List[int]

class GameState(BaseModel):
    stage: GameStage
    pot_size: int
    community_cards: List[Card]
    current_player_idx: int  # Index in players list
    dealer_idx: int
    small_blind_idx: int
    big_blind_idx: int
    min_bet: int
    players: List[Player]
    logs: List[str] = []
    winners: List[int] = []  # List of player IDs
