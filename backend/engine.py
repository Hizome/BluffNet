import random
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from agents import BaseAgent, CallStationAgent, LLMAgent, RandomAgent
from models import ActionType, Card, GameStage, GameState, Player, PlayerAction

try:
    from treys import Evaluator, Card as TreysCard
except ImportError:
    print("Warning: treys not found. Evaluation will be disabled.")
    Evaluator, TreysCard = None, None


class Engine:
    MAX_LOG_ENTRIES = 500

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
        self.pending_to_act: Set[int] = set()

        # Agents map: player_id -> Agent
        self.agents: Dict[int, BaseAgent] = {}
        self.agent_types: Dict[int, str] = {}
        self.agent_profiles: Dict[int, Optional[str]] = {}

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
            # Default lineup: 2 LLM players + others random
            if i == 0:
                self.set_agent_config(i, agent_type="llm", profile="AI1")
            elif i == 1:
                self.set_agent_config(i, agent_type="llm", profile="AI2")
            else:
                self.set_agent_config(i, agent_type="random")

        if Evaluator:
            self.evaluator = Evaluator()
        else:
            self.evaluator = None

    def _build_agent(self, player_id: int, agent_type: str, profile: Optional[str] = None) -> BaseAgent:
        normalized = agent_type.strip().lower()
        if normalized == "llm":
            return LLMAgent(player_id=player_id, profile=profile)
        if normalized == "call_station":
            return CallStationAgent(player_id=player_id)
        if normalized == "random":
            return RandomAgent(player_id=player_id)
        raise ValueError(f"Unsupported agent type: {agent_type}")

    def set_agent_config(self, player_id: int, agent_type: str, profile: Optional[str] = None):
        if player_id < 0 or player_id >= self.n_players:
            raise ValueError(f"Invalid player id: {player_id}")
        normalized = agent_type.strip().lower()
        clean_profile = profile.strip() if isinstance(profile, str) and profile.strip() else None
        if normalized != "llm":
            clean_profile = None
        self.agents[player_id] = self._build_agent(player_id, normalized, clean_profile)
        self.agent_types[player_id] = normalized
        self.agent_profiles[player_id] = clean_profile
        config_log = (
            f"[Config] Player {player_id} -> agent={normalized}"
            f"{f', profile={clean_profile}' if clean_profile else ''}"
        )
        self._log(config_log)
        print(config_log)

    def get_agent_configs(self) -> List[Dict[str, Optional[str]]]:
        configs: List[Dict[str, Optional[str]]] = []
        for p in self.players:
            configs.append(
                {
                    "player_id": p.id,
                    "agent_type": self.agent_types.get(p.id, "random"),
                    "profile": self.agent_profiles.get(p.id),
                }
            )
        return configs

    def set_all_agents_llm(self, profiles: Optional[List[Optional[str]]] = None):
        for i in range(self.n_players):
            profile = None
            if profiles and i < len(profiles):
                profile = profiles[i]
            self.set_agent_config(i, agent_type="llm", profile=profile)

    def _log(self, message: str):
        self.logs.append(message)
        if len(self.logs) > self.MAX_LOG_ENTRIES:
            self.logs = self.logs[-self.MAX_LOG_ENTRIES :]

    def _reset_deck(self):
        suits = ["s", "h", "d", "c"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
        self.deck = [Card(suit=s, rank=r) for s in suits for r in ranks]
        random.shuffle(self.deck)

    def _can_player_act(self, player: Player) -> bool:
        return player.is_active and not player.is_all_in

    def _active_players(self) -> List[Player]:
        return [p for p in self.players if p.is_active]

    def _reset_betting_round(self):
        self.pending_to_act = {p.id for p in self.players if self._can_player_act(p)}

    def _find_next_actor(self, start_idx: int) -> Optional[int]:
        if not self.pending_to_act:
            return None

        for offset in range(1, self.n_players + 1):
            idx = (start_idx + offset) % self.n_players
            player = self.players[idx]
            if player.id in self.pending_to_act and self._can_player_act(player):
                return idx
        return None

    def _is_betting_round_complete(self) -> bool:
        acting_players = [p for p in self.players if self._can_player_act(p)]
        if not acting_players:
            return True

        if self.pending_to_act:
            return False

        return all(p.current_bet == self.highest_bet for p in acting_players)

    def start_new_hand(self):
        self._reset_deck()
        self.community_cards = []
        self.pot = 0
        self.stage = GameStage.PREFLOP
        self.winners = []
        self.hand_count += 1

        self._log(f"--- Hand #{self.hand_count} Started ---")

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
            p.thought = ""
            p.total_hand_bet = 0

        # Blinds
        self.highest_bet = self.min_bet
        self._post_blind(sb_idx, self.min_bet // 2)
        self._post_blind(bb_idx, self.min_bet)
        self.last_raiser_idx = bb_idx

        # Deal
        for _ in range(2):
            for p in self.players:
                if p.is_active:
                    p.cards.append(self.deck.pop())

        # Action starts UTG
        self.current_player_idx = (bb_idx + 1) % self.n_players
        self._reset_betting_round()
        next_actor = self._find_next_actor((self.current_player_idx - 1) % self.n_players)
        if next_actor is not None:
            self.current_player_idx = next_actor

        return self.get_state()

    def _post_blind(self, player_idx, amount):
        p = self.players[player_idx]
        actual = min(p.chips, amount)
        p.chips -= actual
        p.current_bet = actual
        self.pot += actual
        p.total_hand_bet += actual
        p.is_all_in = p.chips == 0
        p.last_action = f"Blind ${actual}"
        self._log(f"{p.name} posts blind ${actual}")

    async def step(self):
        """Execute one turn/step of the game."""
        if self.stage == GameStage.SHOWDOWN:
            return self.get_state()

        curr_player = self.players[self.current_player_idx]
        if not self._can_player_act(curr_player):
            next_idx = self._find_next_actor(self.current_player_idx)
            if next_idx is None:
                self._runout_to_showdown()
                return self.get_state()
            self.current_player_idx = next_idx
            curr_player = self.players[self.current_player_idx]

        agent = self.agents[curr_player.id]
        state = self.get_state()
        action, thought = await agent.get_action(state)

        # Normalize Action (force invalid intents into legal moves)
        original_type = action.type
        if action.type == ActionType.CHECK and self.highest_bet > curr_player.current_bet:
            action.type = ActionType.CALL
        if action.type == ActionType.CALL and self.highest_bet == curr_player.current_bet:
            action.type = ActionType.CHECK

        if action.type == ActionType.RAISE:
            min_raise_to = self.highest_bet + self.min_bet
            raise_to = max(min_raise_to, action.amount)
            required = raise_to - curr_player.current_bet
            if required <= 0:
                action.type = ActionType.CHECK if self.highest_bet == curr_player.current_bet else ActionType.CALL
            elif curr_player.chips < required:
                action.type = ActionType.CALL
            else:
                action.amount = raise_to

        if action.type != original_type:
            curr_player.thought = f"[{action.type.value}] {thought}"
        else:
            curr_player.thought = thought

        if action.type == ActionType.FOLD:
            curr_player.last_action = "Fold"
            log_entry = f"{curr_player.name} folds"
        elif action.type == ActionType.CHECK:
            curr_player.last_action = "Check"
            log_entry = f"{curr_player.name} checks"
        elif action.type == ActionType.CALL:
            to_call = max(0, self.highest_bet - curr_player.current_bet)
            amount = min(curr_player.chips, to_call)
            curr_player.last_action = f"Call ${amount}"
            log_entry = f"{curr_player.name} calls ${amount}"
            if amount < to_call:
                log_entry = f"{curr_player.name} calls ${amount} (all-in)"
        elif action.type == ActionType.RAISE:
            curr_player.last_action = f"Raise to ${action.amount}"
            log_entry = f"{curr_player.name} raises to ${action.amount}"
        else:
            curr_player.last_action = "Check"
            log_entry = f"{curr_player.name} checks"
            action.type = ActionType.CHECK

        self._apply_action(curr_player, action)
        self._log(log_entry)

        self.pending_to_act.discard(curr_player.id)
        if action.type == ActionType.RAISE:
            self.last_raiser_idx = curr_player.id
            self.pending_to_act = {
                p.id
                for p in self.players
                if self._can_player_act(p) and p.id != curr_player.id
            }

        active_players = self._active_players()
        if len(active_players) == 1:
            self._determine_winner()
            return self.get_state()

        if self._is_betting_round_complete():
            self.next_stage()
            return self.get_state()

        next_idx = self._find_next_actor(self.current_player_idx)
        if next_idx is None:
            self._runout_to_showdown()
            return self.get_state()

        self.current_player_idx = next_idx
        return self.get_state()

    def _apply_action(self, player: Player, action: PlayerAction):
        if action.type == ActionType.FOLD:
            player.is_active = False
            player.last_action = "Fold"
            self.pending_to_act.discard(player.id)
            return
        elif action.type == ActionType.CHECK:
            return

        if action.type == ActionType.CALL:
            to_call = self.highest_bet - player.current_bet
            amount = min(player.chips, to_call)
            player.chips -= amount
            player.current_bet += amount
            self.pot += amount
            player.total_hand_bet += amount
            if player.chips == 0:
                player.is_all_in = True
            return

        elif action.type == ActionType.RAISE:
            min_raise_to = self.highest_bet + self.min_bet
            raise_to = max(min_raise_to, action.amount)
            amount_needed = raise_to - player.current_bet

            if amount_needed <= 0:
                return

            if player.chips >= amount_needed:
                player.chips -= amount_needed
                player.current_bet += amount_needed
                self.pot += amount_needed
                player.total_hand_bet += amount_needed
                self.highest_bet = player.current_bet
                if player.chips == 0:
                    player.is_all_in = True
            else:
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
            return

        # Reset Round State
        self.highest_bet = 0
        for p in self.players:
            p.current_bet = 0
            p.last_action = ""

        # Action starts after button
        self._reset_betting_round()
        next_actor = self._find_next_actor(self.dealer_idx)
        if next_actor is None:
            self._runout_to_showdown()
            return
        self.current_player_idx = next_actor
        self.last_raiser_idx = self.current_player_idx

    def _runout_to_showdown(self):
        if self.stage == GameStage.SHOWDOWN:
            return

        while len(self.community_cards) < 5:
            self.community_cards.append(self.deck.pop())

        self.stage = GameStage.SHOWDOWN
        self._determine_winner()

    def _to_treys_card(self, card: Card) -> int:
        return TreysCard.new(f"{card.rank}{card.suit}")

    def _build_side_pots(self) -> List[Tuple[int, List[int]]]:
        contributions = {p.id: p.total_hand_bet for p in self.players if p.total_hand_bet > 0}
        if not contributions:
            active_ids = [p.id for p in self._active_players()]
            return [(self.pot, active_ids)] if active_ids else []

        levels = sorted(set(contributions.values()))
        prev = 0
        side_pots: List[Tuple[int, List[int]]] = []
        for level in levels:
            participants = [pid for pid, amt in contributions.items() if amt >= level]
            pot_amount = (level - prev) * len(participants)
            prev = level
            if pot_amount <= 0:
                continue
            eligible = [pid for pid in participants if self.players[pid].is_active]
            if eligible:
                side_pots.append((pot_amount, eligible))
        return side_pots

    def _split_pot(self, amount: int, winner_ids: List[int], payouts: Dict[int, int]):
        if amount <= 0 or not winner_ids:
            return

        start = (self.dealer_idx + 1) % self.n_players
        ordered_winners = sorted(winner_ids, key=lambda pid: (pid - start) % self.n_players)
        base = amount // len(ordered_winners)
        remainder = amount % len(ordered_winners)
        for winner_id in ordered_winners:
            payouts[winner_id] += base
        for i in range(remainder):
            payouts[ordered_winners[i]] += 1

    def _determine_winner(self):
        active = self._active_players()
        if not active:
            return

        payouts: Dict[int, int] = defaultdict(int)
        if len(active) == 1:
            payouts[active[0].id] = self.pot
        elif self.evaluator and TreysCard and len(self.community_cards) == 5:
            board = [self._to_treys_card(c) for c in self.community_cards]
            scores: Dict[int, int] = {}
            for player in active:
                hand = [self._to_treys_card(c) for c in player.cards]
                scores[player.id] = self.evaluator.evaluate(board, hand)

            side_pots = self._build_side_pots()
            distributed = 0
            for pot_amount, eligible_ids in side_pots:
                eligible_scores = {pid: scores[pid] for pid in eligible_ids if pid in scores}
                if not eligible_scores:
                    continue
                best_score = min(eligible_scores.values())
                pot_winners = [pid for pid, score in eligible_scores.items() if score == best_score]
                self._split_pot(pot_amount, pot_winners, payouts)
                distributed += pot_amount

            if distributed < self.pot:
                best_score = min(scores.values())
                fallback_winners = [pid for pid, score in scores.items() if score == best_score]
                self._split_pot(self.pot - distributed, fallback_winners, payouts)
        else:
            winner = random.choice(active)
            payouts[winner.id] = self.pot
            self._log("evaluator unavailable, winner selected randomly.")

        for player_id, amount in payouts.items():
            self.players[player_id].chips += amount

        self.winners = sorted([pid for pid, amount in payouts.items() if amount > 0])
        for winner_id in self.winners:
            self.players[winner_id].stats["wins"] += 1
            self._log(f"{self.players[winner_id].name} wins ${payouts[winner_id]}!")

        for p in self.players:
            if p.total_hand_bet > 0:
                p.stats["hands_played"] += 1

        self.pot = 0
        self.pending_to_act = set()

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
