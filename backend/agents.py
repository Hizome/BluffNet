from abc import ABC, abstractmethod
import random
import json
from typing import Tuple, List, Optional
from models import GameState, PlayerAction, ActionType

class BaseAgent(ABC):
    def __init__(self, player_id: int):
        self.player_id = player_id

    @abstractmethod
    async def get_action(self, game_state: GameState) -> Tuple[PlayerAction, str]:
        pass

class RandomAgent(BaseAgent):
    async def get_action(self, game_state: GameState) -> Tuple[PlayerAction, str]:
        # Identify "to call" amount
        me = next(p for p in game_state.players if p.id == self.player_id)
        # Calculate highest bet manually since it's not in GameState yet
        highest_bet = max([p.current_bet for p in game_state.players] + [0])
        to_call = highest_bet - me.current_bet

        if to_call > 0:
            valid_actions = [ActionType.CALL, ActionType.FOLD, ActionType.RAISE]
        else:
            valid_actions = [ActionType.CHECK, ActionType.RAISE]
        
        act_type = random.choice(valid_actions)
        
        if act_type == ActionType.RAISE:
            # Simple random raise
            amount = game_state.min_bet
            thought = f"I'm feeling spicy, let's raise to build the pot!"
            return PlayerAction(type=act_type, amount=highest_bet + amount), thought
            
        thought = f"I think {act_type.value} is a safe move here."
        return PlayerAction(type=act_type), thought

class CallStationAgent(BaseAgent):
    async def get_action(self, game_state: GameState) -> Tuple[PlayerAction, str]:
        return PlayerAction(type=ActionType.CALL), "I will maximize VPIP!"

class LLMAgent(BaseAgent):
    def __init__(self, player_id: int, profile: str = None):
        super().__init__(player_id)
        self.profile = profile
        from llm_client import LLMClient
        self.client = LLMClient()

    async def get_action(self, game_state: GameState) -> Tuple[PlayerAction, str]:
        me = next(p for p in game_state.players if p.id == self.player_id)
        system_prompt = f"""You are a Texas Hold'em poker player. Your persona is: {me.persona}.
Your goal is to win chips. You must respond in a valid JSON format.
JSON Schema: {{ "action": "FOLD" | "CHECK" | "CALL" | "RAISE", "amount": number, "thought": string }}
"""
        state_brief = {
            "stage": game_state.stage,
            "pot": game_state.pot_size,
            "my_chips": me.chips,
            "my_cards": [str(c) for c in me.cards],
            "community": [str(c) for c in game_state.community_cards],
            "min_bet": game_state.min_bet,
            "players": [{"name": p.name, "chips": p.chips, "active": p.is_active} for p in game_state.players]
        }
        prompt = f"Current Game State: {json.dumps(state_brief)}\nWhat is your next move?"
        
        response_text = await self.client.call(prompt, system_prompt, profile=self.profile)
        
        try:
            # Basic cleanup if LLM returns markdown blocks
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:-3].strip()
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:-3].strip()
                
            res = json.loads(clean_text)
            action_type = ActionType(res.get("action", "CHECK").upper())
            thought = res.get("thought", "Thinking...")
            return PlayerAction(type=action_type, amount=res.get("amount", 0)), thought
        except Exception as e:
            print(f"LLM Parsing Error: {e}")
            return PlayerAction(type=ActionType.CHECK), "My brain skipped a beat."
