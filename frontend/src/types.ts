export interface Card {
    suit: string
    rank: string
}

export interface Player {
    id: number
    name: string
    chips: number
    cards: Card[]
    is_active: boolean
    is_all_in: boolean
    current_bet: number
    position: number
    persona: string
    thought: string
    last_action: string
    total_hand_bet: number
    stats: { wins: number; hands_played: number }
}

export interface GameState {
    stage: string // PREFLOP, FLOP, etc
    pot_size: number
    hand_count: number
    community_cards: Card[]
    current_player_idx: number
    dealer_idx: number
    small_blind_idx: number
    big_blind_idx: number
    min_bet: number
    players: Player[]
    logs: string[]
    winners: number[]
}

export interface LLMProfileInfo {
    profile: string
    model: string
    base_url: string
    has_api_key: boolean
}

export interface AgentRuntimeConfig {
    player_id: number
    agent_type: string
    profile: string | null
    llm?: LLMProfileInfo
}
