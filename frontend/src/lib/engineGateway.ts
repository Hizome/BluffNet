import type { Card, GameState, Player } from '../types'

export type EngineMode = 'connecting' | 'remote' | 'local'

type EngineGatewayOptions = {
  tableId: string
  onModeChange?: (mode: EngineMode) => void
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

const createDeck = () => {
  const suits = ['s', 'h', 'd', 'c']
  const ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
  const deck: Card[] = []
  for (const s of suits) {
    for (const r of ranks) {
      deck.push({ suit: s, rank: r })
    }
  }
  for (let i = deck.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    const temp = deck[i]!
    deck[i] = deck[j]!
    deck[j] = temp
  }
  return deck
}

class LocalEngine {
  private nPlayers = 8
  private initialChips = 1000
  private state: GameState
  private deck: Card[] = []
  private highestBet = 0
  private actionsThisStreet = 0

  constructor() {
    const players: Player[] = []
    for (let i = 0; i < this.nPlayers; i++) {
      players.push({
        id: i,
        name: `AI ${i + 1}`,
        chips: this.initialChips,
        cards: [],
        is_active: true,
        is_all_in: false,
        current_bet: 0,
        position: i,
        persona: `Local fallback agent ${i + 1}`,
        thought: '',
        last_action: '',
        total_hand_bet: 0,
        stats: { wins: 0, hands_played: 0 },
      })
    }
    this.state = {
      stage: 'PREFLOP',
      pot_size: 0,
      hand_count: 0,
      community_cards: [],
      current_player_idx: 0,
      dealer_idx: 0,
      small_blind_idx: 1,
      big_blind_idx: 2,
      min_bet: 20,
      players,
      logs: [],
      winners: [],
    }
  }

  private log(message: string) {
    this.state.logs.push(message)
    if (this.state.logs.length > 300) {
      this.state.logs = this.state.logs.slice(-300)
    }
  }

  private getPlayer(idx: number): Player {
    const p = this.state.players[idx]
    if (!p) throw new Error(`Invalid player index: ${idx}`)
    return p
  }

  private firstActiveFrom(start: number): number | null {
    for (let i = 1; i <= this.nPlayers; i++) {
      const idx = (start + i) % this.nPlayers
      const p = this.getPlayer(idx)
      if (p.is_active && !p.is_all_in) return idx
    }
    return null
  }

  private postBlind(idx: number, amount: number) {
    const p = this.getPlayer(idx)
    if (!p.is_active) return
    const actual = Math.min(amount, p.chips)
    p.chips -= actual
    p.current_bet += actual
    p.total_hand_bet += actual
    p.is_all_in = p.chips === 0
    p.last_action = `Blind $${actual}`
    this.state.pot_size += actual
    this.highestBet = Math.max(this.highestBet, p.current_bet)
    this.log(`${p.name} posts blind $${actual}`)
  }

  private activePlayers() {
    return this.state.players.filter((p) => p.is_active)
  }

  private advanceStreet() {
    this.actionsThisStreet = 0
    for (const p of this.state.players) {
      p.current_bet = 0
      p.last_action = ''
    }
    this.highestBet = 0

    if (this.state.stage === 'PREFLOP') {
      this.state.stage = 'FLOP'
      this.state.community_cards.push(this.deck.pop()!, this.deck.pop()!, this.deck.pop()!)
      return
    }
    if (this.state.stage === 'FLOP') {
      this.state.stage = 'TURN'
      this.state.community_cards.push(this.deck.pop()!)
      return
    }
    if (this.state.stage === 'TURN') {
      this.state.stage = 'RIVER'
      this.state.community_cards.push(this.deck.pop()!)
      return
    }
    if (this.state.stage === 'RIVER') {
      this.finishHand()
    }
  }

  private finishHand() {
    this.state.stage = 'SHOWDOWN'
    const alive = this.activePlayers()
    if (alive.length === 0) return
    const winner = alive[Math.floor(Math.random() * alive.length)]
    if (!winner) return
    winner.chips += this.state.pot_size
    winner.stats.wins += 1
    this.state.winners = [winner.id]
    this.log(`${winner.name} wins $${this.state.pot_size}!`)
    for (const p of this.state.players) {
      if (p.total_hand_bet > 0) p.stats.hands_played += 1
    }
    this.state.pot_size = 0
  }

  async getState() {
    return structuredClone(this.state)
  }

  async startGame() {
    this.deck = createDeck()
    this.state.hand_count += 1
    this.state.stage = 'PREFLOP'
    this.state.community_cards = []
    this.state.winners = []
    this.state.pot_size = 0
    this.actionsThisStreet = 0
    this.highestBet = 0

    this.state.dealer_idx = (this.state.dealer_idx + 1) % this.nPlayers
    this.state.small_blind_idx = (this.state.dealer_idx + 1) % this.nPlayers
    this.state.big_blind_idx = (this.state.dealer_idx + 2) % this.nPlayers

    for (const p of this.state.players) {
      p.cards = []
      p.current_bet = 0
      p.is_active = p.chips > 0
      p.is_all_in = false
      p.last_action = ''
      p.thought = ''
      p.total_hand_bet = 0
    }

    this.log(`--- Hand #${this.state.hand_count} Started ---`)
    this.postBlind(this.state.small_blind_idx, Math.floor(this.state.min_bet / 2))
    this.postBlind(this.state.big_blind_idx, this.state.min_bet)

    for (let k = 0; k < 2; k++) {
      for (const p of this.state.players) {
        if (p.is_active) p.cards.push(this.deck.pop()!)
      }
    }

    this.state.current_player_idx = (this.state.big_blind_idx + 1) % this.nPlayers
    const next = this.firstActiveFrom((this.state.current_player_idx - 1 + this.nPlayers) % this.nPlayers)
    if (next !== null) this.state.current_player_idx = next

    return this.getState()
  }

  async resetCycle() {
    this.state.logs = []
    this.state.hand_count = 0
    this.state.dealer_idx = 0
    for (const p of this.state.players) {
      p.chips = this.initialChips
      p.stats = { wins: 0, hands_played: 0 }
    }
    return this.startGame()
  }

  async nextStep() {
    if (this.state.stage === 'SHOWDOWN') return this.getState()

    const alive = this.activePlayers()
    if (alive.length <= 1) {
      this.finishHand()
      return this.getState()
    }

    const me = this.getPlayer(this.state.current_player_idx)
    if (!me.is_active || me.is_all_in) {
      const next = this.firstActiveFrom(this.state.current_player_idx)
      if (next === null) {
        this.finishHand()
      } else {
        this.state.current_player_idx = next
      }
      return this.getState()
    }

    const toCall = Math.max(0, this.highestBet - me.current_bet)
    const choices = toCall > 0 ? ['CALL', 'FOLD', 'RAISE'] : ['CHECK', 'RAISE']
    const picked = choices[Math.floor(Math.random() * choices.length)]

    if (picked === 'FOLD') {
      me.is_active = false
      me.last_action = 'Fold'
      me.thought = 'local fallback fold'
      this.log(`${me.name} folds`)
    } else if (picked === 'CHECK') {
      me.last_action = 'Check'
      me.thought = 'local fallback check'
      this.log(`${me.name} checks`)
    } else if (picked === 'CALL') {
      const amount = Math.min(me.chips, toCall)
      me.chips -= amount
      me.current_bet += amount
      me.total_hand_bet += amount
      me.is_all_in = me.chips === 0
      me.last_action = `Call $${amount}`
      me.thought = 'local fallback call'
      this.state.pot_size += amount
      this.log(`${me.name} calls $${amount}`)
    } else {
      const raiseTo = Math.max(this.highestBet + this.state.min_bet, this.highestBet + this.state.min_bet)
      const need = raiseTo - me.current_bet
      const amount = Math.min(me.chips, need)
      me.chips -= amount
      me.current_bet += amount
      me.total_hand_bet += amount
      me.is_all_in = me.chips === 0
      this.highestBet = Math.max(this.highestBet, me.current_bet)
      me.last_action = `Raise to $${me.current_bet}`
      me.thought = 'local fallback raise'
      this.state.pot_size += amount
      this.log(`${me.name} raises to $${me.current_bet}`)
    }

    this.actionsThisStreet += 1
    const activeCount = this.state.players.filter((p) => p.is_active && !p.is_all_in).length
    if (activeCount <= 1) {
      this.finishHand()
      return this.getState()
    }
    if (this.actionsThisStreet >= activeCount) {
      this.advanceStreet()
      return this.getState()
    }

    const next = this.firstActiveFrom(this.state.current_player_idx)
    if (next !== null) this.state.current_player_idx = next
    return this.getState()
  }
}

class RemoteEngine {
  private tableId: string

  constructor(tableId: string) {
    this.tableId = tableId
  }

  private url(path: string) {
    return `${API_BASE_URL}${path}?table_id=${encodeURIComponent(this.tableId)}`
  }

  private async json(path: string, init?: RequestInit) {
    const res = await fetch(this.url(path), init)
    if (!res.ok) {
      throw new Error(`Remote request failed: ${path} status=${res.status}`)
    }
    return (await res.json()) as GameState
  }

  async ping(timeoutMs = 2500) {
    const ctrl = new AbortController()
    const t = window.setTimeout(() => ctrl.abort(), timeoutMs)
    try {
      const res = await fetch(this.url('/status'), { signal: ctrl.signal })
      if (!res.ok) throw new Error(`status=${res.status}`)
    } finally {
      clearTimeout(t)
    }
  }

  async getState() {
    return this.json('/state')
  }

  async startGame() {
    return this.json('/start_game', { method: 'POST' })
  }

  async nextStep() {
    return this.json('/next_step', { method: 'POST' })
  }

  async resetCycle() {
    return this.json('/reset_cycle', { method: 'POST' })
  }
}

export function createEngineGateway(opts: EngineGatewayOptions) {
  let mode: EngineMode = 'connecting'
  const local = new LocalEngine()
  const remote = new RemoteEngine(opts.tableId)
  let probeTimer: number | null = null

  const setMode = (next: EngineMode) => {
    if (mode !== next) {
      mode = next
      opts.onModeChange?.(next)
    }
  }

  const fallbackToLocal = async () => {
    setMode('local')
    const state = await local.getState()
    if (state.hand_count === 0) {
      return local.startGame()
    }
    return state
  }

  const tryRemote = async () => {
    await remote.ping()
    setMode('remote')
  }

  const withAutoFallback = async (remoteCall: () => Promise<GameState>, localCall: () => Promise<GameState>) => {
    if (mode === 'remote') {
      try {
        return await remoteCall()
      } catch {
        setMode('local')
        return localCall()
      }
    }
    return localCall()
  }

  const startProbe = () => {
    if (probeTimer !== null) return
    probeTimer = window.setInterval(async () => {
      if (mode !== 'local') return
      try {
        await tryRemote()
      } catch {
        // keep local mode
      }
    }, 8000)
  }

  const stopProbe = () => {
    if (probeTimer !== null) {
      clearInterval(probeTimer)
      probeTimer = null
    }
  }

  return {
    getMode: () => mode,
    async init() {
      try {
        await tryRemote()
        return await remote.getState()
      } catch {
        return fallbackToLocal()
      }
    },
    startProbe,
    stopProbe,
    getState: () => withAutoFallback(() => remote.getState(), () => local.getState()),
    startGame: () => withAutoFallback(() => remote.startGame(), () => local.startGame()),
    nextStep: () => withAutoFallback(() => remote.nextStep(), () => local.nextStep()),
    resetCycle: () => withAutoFallback(() => remote.resetCycle(), () => local.resetCycle()),
  }
}
