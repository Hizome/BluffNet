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
        highest_bet = max([p.current_bet for p in game_state.players] + [0])
        to_call = max(0, highest_bet - me.current_bet)
        min_raise_to = highest_bet + game_state.min_bet
        max_raise_to = me.current_bet + me.chips

        legal_actions: List[str] = ["FOLD"]
        if to_call == 0:
            legal_actions.append("CHECK")
        else:
            legal_actions.append("CALL")
        if me.chips > to_call and max_raise_to >= min_raise_to:
            legal_actions.append("RAISE")

        system_prompt = f"""You are a fast Texas Hold'em poker player. Your persona is: {me.persona}.
Decide quickly and return compact JSON only.
No markdown, no long explanation, no extra text.
JSON Schema: {{ "action": "FOLD" | "CHECK" | "CALL" | "RAISE", "amount": number, "thought": string }}
Rules:
- Choose action only from legal_actions.
- If action is RAISE, set amount within [min_raise_to, max_raise_to].
- thought must be short (max 50 words). Empty string is allowed.
"""
        state_brief = {
            "stage": game_state.stage,
            "pot": game_state.pot_size,
            "my_chips": me.chips,
            "my_cards": [str(c) for c in me.cards],
            "community": [str(c) for c in game_state.community_cards],
            "min_bet": game_state.min_bet,
            "highest_bet": highest_bet,
            "to_call": to_call,
            "legal_actions": legal_actions,
            "raise_bounds": {
                "min_raise_to": min_raise_to,
                "max_raise_to": max_raise_to,
            },
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
            action_str = str(res.get("action", "CHECK")).upper()
            if action_str not in legal_actions:
                if "CHECK" in legal_actions:
                    action_str = "CHECK"
                elif "CALL" in legal_actions:
                    action_str = "CALL"
                else:
                    action_str = "FOLD"
            action_type = ActionType(action_str)
            thought = res.get("thought", "Thinking...")
            amount = int(res.get("amount", 0) or 0)
            if action_type == ActionType.RAISE:
                amount = max(min_raise_to, min(max_raise_to, amount))
            else:
                amount = 0
            return PlayerAction(type=action_type, amount=amount), thought
        except Exception as e:
            print(f"LLM Parsing Error: {e}")
            if "CHECK" in legal_actions:
                return PlayerAction(type=ActionType.CHECK), "My brain skipped a beat."
            if "CALL" in legal_actions:
                return PlayerAction(type=ActionType.CALL), "My brain skipped a beat."
            return PlayerAction(type=ActionType.FOLD), "My brain skipped a beat."
