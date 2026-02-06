import random
from typing import List, Dict, Optional
from models import GameState, Player, Card, GameStage, ActionType, PlayerAction
from agents import BaseAgent, RandomAgent, CallStationAgent, LLMAgent

try:
    from treys import Deck as TreysDeck, Evaluator, Card as TreysCard
except ImportError:
    print("Warning: treys not found. Evaluation will be disabled.")
    TreysDeck, Evaluator, TreysCard = None, None, None

class Engine:
    def __init__(self, n_players=8):
        self.n_players = n_players
        self.players: List[Player] = []
        self.community_cards: List[Card] = []
        self.deck = []
        self.stage = GameStage.PREFLOP
        self.pot = 0
        self.dealer_idx = 0
        self.current_player_idx = 0
        self.min_bet = 20
        self.highest_bet = 0
        self.last_raiser_idx = -1
        self.logs: List[str] = []
        self.hand_count = 0
        self.winners: List[int] = []
        
        # Agents map: player_id -> Agent
        self.agents: Dict[int, BaseAgent] = {}

        # Initialize players and agents
        for i in range(n_players):
            self.players.append(Player(
                id=i,
                name=f"AI {i+1}",
                chips=1000,
                position=i,
                persona=f"Agent based on randomized logic {i+1}",
                last_action="",
                total_hand_bet=0,
                stats={"wins": 0, "hands_played": 0}
            ))
            # Assign LLMAgent with profiles
            if i == 0:
                self.agents[i] = LLMAgent(player_id=i, profile="AI1")
            elif i == 1:
                self.agents[i] = LLMAgent(player_id=i, profile="AI2")
            else:
                self.agents[i] = RandomAgent(player_id=i)
            
        if Evaluator:
            self.evaluator = Evaluator()
        else:
            self.evaluator = None

    def _reset_deck(self):
        suits = ['s', 'h', 'd', 'c']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        self.deck = [Card(suit=s, rank=r) for s in suits for r in ranks]
        random.shuffle(self.deck)

    def start_new_hand(self):
        self._reset_deck()
        self.community_cards = []
        self.pot = 0
        self.stage = GameStage.PREFLOP
        self.winners = []
        self.hand_count += 1
        
        self.logs.append(f"--- Hand #{self.hand_count} Started ---")
        
        self.dealer_idx = (self.dealer_idx + 1) % self.n_players
        # SB/BB
        sb_idx = (self.dealer_idx + 1) % self.n_players
        bb_idx = (self.dealer_idx + 2) % self.n_players
        
        for p in self.players:
            p.cards = []
            p.current_bet = 0
            p.is_active = (p.chips > 0)
            p.is_all_in = False
            p.last_action = ""
            p.total_hand_bet = 0
            
        # Blinds
        self.highest_bet = self.min_bet
        self._post_blind(sb_idx, self.min_bet // 2)
        self._post_blind(bb_idx, self.min_bet)
        self.last_raiser_idx = bb_idx # Betting ends when it returns to BB (if no raise)
        
        # Deal
        for _ in range(2):
            for p in self.players:
                if p.is_active:
                    p.cards.append(self.deck.pop())
        
        # Action starts UTG
        self.current_player_idx = (bb_idx + 1) % self.n_players
        self._advance_to_active_player()
        
        return self.get_state()

    def _post_blind(self, player_idx, amount):
        p = self.players[player_idx]
        actual = min(p.chips, amount)
        p.chips -= actual
        p.current_bet = actual
        self.pot += actual
        p.total_hand_bet += actual
        p.last_action = f"Blind ${actual}"
        self.logs.append(f"{p.name} posts blind ${actual}")

    def _advance_to_active_player(self):
        start_idx = self.current_player_idx
        while not self.players[self.current_player_idx].is_active or self.players[self.current_player_idx].is_all_in:
             self.current_player_idx = (self.current_player_idx + 1) % self.n_players
             if self.current_player_idx == start_idx:
                 # Should check for showdown if everyone all-in/folded
                 break

    async def step(self):
        """Execute one turn/step of the game."""
        state = self.get_state()
        
        # 0. Check for Showdown/Terminated
        if self.stage == GameStage.SHOWDOWN:
            return state

        # 1. Check if Betting Round Complete
        # Condition: Current player == Last Raiser AND (Current player has matched or is all-in)
        # Actually, simpler: if we circled back to last_raiser_idx and everyone equalized?
        # Let's verify simpler "Round End" condition: 
        #   If matches highest bet, we typically move next... 
        #   Real logic: if current == last_raiser_idx (and he checked/called), round over
        #   BUT: Preflop BB option.
        
        # Simplified Logic for Prototype:
        # Check round completion BEFORE asking action? No, after action.
        
        # 2. Get Agent Action
        curr_player = self.players[self.current_player_idx]
        agent = self.agents[curr_player.id]
        action, thought = await agent.get_action(state)
        
        # Update Thought
        curr_player.thought = thought

        # Normalize Action (Check if valid)
        original_type = action.type
        if action.type == ActionType.CHECK and self.highest_bet > curr_player.current_bet:
            action.type = ActionType.CALL
        if action.type == ActionType.CALL and self.highest_bet == curr_player.current_bet:
            action.type = ActionType.CHECK
            
        # If action was forced to change, append a note to the thought so it's not confusing
        if action.type != original_type:
            curr_player.thought = f"[{action.type.value}] {thought}"
        else:
            curr_player.thought = thought
        
        if action.type == ActionType.FOLD:
             curr_player.last_action = "Fold"
             curr_player.is_active = False 
             log_entry = f"{curr_player.name} folds"
             # Check for early win (Fold Equity)
             active_players = [p for p in self.players if p.is_active]
             if len(active_players) == 1:
                 # Winner determined immediately
                 self.logs.append(log_entry)
                 self._determine_winner()
                 return self.get_state()
                 
        elif action.type == ActionType.CHECK:
             curr_player.last_action = "Check"
             log_entry = f"{curr_player.name} checks"

        elif action.type == ActionType.CALL:
             to_call = self.highest_bet - curr_player.current_bet
             amount = min(curr_player.chips, to_call)
             curr_player.last_action = f"Call ${amount}"
             log_entry = f"{curr_player.name} calls ${amount}"
             if amount < to_call:
                 log_entry = f"{curr_player.name} calls ${amount} (all-in)"
        
        elif action.type == ActionType.RAISE:
             # Calculate raise details
             min_bet_needed = self.highest_bet + self.min_bet
             # Use larger of (agent provided amount) or (min raise)
             raise_to = max(min_bet_needed, action.amount)
             
             # Can player afford it?
             if curr_player.chips >= (raise_to - curr_player.current_bet):
                 curr_player.last_action = f"Raise to ${raise_to}"
                 log_entry = f"{curr_player.name} raises to ${raise_to}"
             else:
                 # Not enough to raise, fallback to Call
                 action.type = ActionType.CALL
                 to_call = self.highest_bet - curr_player.current_bet
                 amount = min(curr_player.chips, to_call)
                 curr_player.last_action = f"Call ${amount}"
                 log_entry = f"{curr_player.name} calls ${amount} (all-in)"

        # 4. Apply Corrected Action
        self._apply_action(curr_player, action)
        
        # Append full log
        self.logs.append(log_entry)
        
        # 4. Move Next or Next Stage
        # If this player RAISED, update last_raiser
        if action.type == ActionType.RAISE:
            self.last_raiser_idx = curr_player.id
            
        # Check if round is done
        next_idx = (self.current_player_idx + 1) % self.n_players
        
        # Special case: If we just acted, and now the NEXT player is the last_raiser_idx, 
        # and everyone is equal... logic is tricky. 
        # Alternate: Track "players to act".
        # Let's use: if next active player == last_raiser_idx, AND everyone balanced -> Next Stage.
        
        if next_idx == self.last_raiser_idx:
             # Everyone had a chance?
             # Check if all active players matched highest_bet
             all_matched = True
             for p in self.players:
                 if p.is_active and not p.is_all_in and p.current_bet < self.highest_bet:
                     all_matched = False
                     break
             
             if all_matched:
                 self.next_stage()
                 return self.get_state()

        # Advance
        self.current_player_idx = next_idx
        self._advance_to_active_player()
        
        return self.get_state()

    def _apply_action(self, player: Player, action: PlayerAction):
        # Validation / Forced Correction
        if action.type == ActionType.FOLD:
            player.is_active = False
        elif action.type == ActionType.CHECK:
            if player.current_bet < self.highest_bet:
                # Cannot check if bet > current, force CALL
                action.type = ActionType.CALL
                
        if action.type == ActionType.CALL:
            to_call = self.highest_bet - player.current_bet
            amount = min(player.chips, to_call)
            player.chips -= amount
            player.current_bet += amount
            self.pot += amount
            player.total_hand_bet += amount
            if amount < to_call:
                player.is_all_in = True
                
        elif action.type == ActionType.RAISE:
            # Min raise = 2x previous raise diff... simplified to min_bet
            # Force raise to be at least highest + min_bet
            # Simple Agent might set type RAISE but 0 amount
            min_raise = self.highest_bet + self.min_bet
            amount_needed = min_raise - player.current_bet
            
            if player.chips >= amount_needed:
                player.chips -= amount_needed
                player.current_bet += amount_needed
                self.pot += amount_needed
                player.total_hand_bet += amount_needed
                self.highest_bet = player.current_bet
                # self.last_raiser_idx = player.id (handled in step)
            else:
                # Not enough to raise -> All In Call
                self._apply_action(player, PlayerAction(type=ActionType.CALL))


    def next_stage(self):
        if self.stage == GameStage.PREFLOP:
            self.stage = GameStage.FLOP
            self.community_cards.extend([self.deck.pop() for _ in range(3)])
        elif self.stage == GameStage.FLOP:
            self.stage = GameStage.TURN
            self.community_cards.append(self.deck.pop())
        elif self.stage == GameStage.TURN:
            self.stage = GameStage.RIVER
            self.community_cards.append(self.deck.pop())
        elif self.stage == GameStage.RIVER:
            self.stage = GameStage.SHOWDOWN
            self._determine_winner()
            return # End
            
        # Reset Round State
        self.highest_bet = 0
        for p in self.players:
            p.current_bet = 0
            # Optional: Clear last action on new street? Or keep until next act?
            # Keeping it helps see history. But "Blind" from Preflop lingering in River is bad.
            # Let's clear it.
            p.last_action = ""
        
        # Action starts after button
        self.current_player_idx = (self.dealer_idx + 1) % self.n_players
        self._advance_to_active_player()
        self.last_raiser_idx = self.current_player_idx # First to act is now the pivot

    def _determine_winner(self):
        active = [p for p in self.players if p.is_active]
        if not active: return
        winner = random.choice(active) # TODO: Real eval
        winner.chips += self.pot
        winner.stats["wins"] += 1
        self.logs.append(f"🏆 {winner.name} wins ${self.pot}!")
        self.winners = [winner.id]
        
        # Update hands played for all who participated (simplified: all players)
        for p in self.players:
            p.stats["hands_played"] += 1
            
        self.pot = 0

    def get_state(self) -> GameState:
        return GameState(
            stage=self.stage,
            pot_size=self.pot,
            community_cards=self.community_cards,
            current_player_idx=self.current_player_idx,
            dealer_idx=self.dealer_idx,
            small_blind_idx=(self.dealer_idx + 1) % self.n_players,
            big_blind_idx=(self.dealer_idx + 2) % self.n_players,
            min_bet=self.min_bet,
            players=self.players,
            logs=self.logs,
            winners=self.winners
        )
