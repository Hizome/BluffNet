<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { createEngineGateway } from '../lib/engineGateway'
import type { GameState } from '../types'

const backendStatus = ref('Connecting...')
const godMode = ref(false)
const gameState = ref<GameState | null>(null)
let pollInterval: number | null = null
const TABLE_ID_KEY = 'bluffnet_table_id'

const ensureTableId = () => {
  let id = localStorage.getItem(TABLE_ID_KEY)
  if (!id) {
    id = (crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`)
    localStorage.setItem(TABLE_ID_KEY, id)
  }
  return id
}

const tableId = ensureTableId()
const engineGateway = createEngineGateway({
  tableId,
  onModeChange: (mode) => {
    if (mode === 'remote') backendStatus.value = 'Online (Cloud)'
    else if (mode === 'local') backendStatus.value = 'Local Fallback'
    else backendStatus.value = 'Connecting...'
  },
})

// Suit Mapping
const suitMap: Record<string, { symbol: string, color: string }> = {
  's': { symbol: '♠', color: 'text-black' },
  'h': { symbol: '♥', color: 'text-red-500' },
  'd': { symbol: '♦', color: 'text-red-500' },
  'c': { symbol: '♣', color: 'text-black' }, 
}

const getCardColor = (suit: string) => suitMap[suit]?.color || 'text-black'
const getCardSymbol = (suit: string) => suitMap[suit]?.symbol || suit

const isProcessing = ref(false)
const pinnedThoughtPlayerId = ref<number | null>(null)
const autoMode = ref(false)
const autoCycleHands = ref(10)
const autoTargetHandCount = ref<number | null>(null)
let autoTickTimer: number | null = null
const AUTO_RETRY_DELAY_MS = 400
const AUTO_AFTER_RESTART_DELAY_MS = 1800
const AUTO_STEP_DELAY_MS = 1700

const clearAutoTimer = () => {
  if (autoTickTimer !== null) {
    clearTimeout(autoTickTimer)
    autoTickTimer = null
  }
}

const scheduleAutoTick = (delayMs = 0) => {
  clearAutoTimer()
  if (!autoMode.value) return
  autoTickTimer = window.setTimeout(() => {
    runAutoTick()
  }, delayMs)
}

const fetchState = async () => {
  try {
    const data: GameState = await engineGateway.getState()
    gameState.value = data
    const mode = engineGateway.getMode()
    backendStatus.value = mode === 'remote' ? 'Online (Cloud)' : mode === 'local' ? 'Local Fallback' : 'Connecting...'
  } catch (e) {
    backendStatus.value = 'Offline'
  }
}

const nextStep = async () => {
  if (isProcessing.value) return
  isProcessing.value = true
  try {
    const data = await engineGateway.nextStep()
    gameState.value = data
    const mode = engineGateway.getMode()
    backendStatus.value = mode === 'remote' ? 'Online (Cloud)' : mode === 'local' ? 'Local Fallback' : 'Connecting...'
  } finally {
    isProcessing.value = false
  }
}

const startGame = async () => {
  if (isProcessing.value) return
  isProcessing.value = true
  try {
    const data = await engineGateway.startGame()
    gameState.value = data
    const mode = engineGateway.getMode()
    backendStatus.value = mode === 'remote' ? 'Online (Cloud)' : mode === 'local' ? 'Local Fallback' : 'Connecting...'
  } finally {
    isProcessing.value = false
  }
}

const resetCycle = async () => {
  if (isProcessing.value) return
  isProcessing.value = true
  try {
    const data = await engineGateway.resetCycle()
    gameState.value = data
    const mode = engineGateway.getMode()
    backendStatus.value = mode === 'remote' ? 'Online (Cloud)' : mode === 'local' ? 'Local Fallback' : 'Connecting...'
  } finally {
    isProcessing.value = false
  }
}

const runAutoTick = async () => {
  if (!autoMode.value) return
  if (isProcessing.value) {
    scheduleAutoTick(AUTO_RETRY_DELAY_MS)
    return
  }

  if (!gameState.value) {
    await fetchState()
    scheduleAutoTick(AUTO_RETRY_DELAY_MS)
    return
  }

  if (gameState.value.stage === 'SHOWDOWN') {
    const cycleSize = autoCycleHands.value
    const target = autoTargetHandCount.value
    const reachedTarget = target !== null && gameState.value.hand_count >= target
    if (cycleSize > 0 && reachedTarget) {
      await resetCycle()
      // After first custom cycle, continue normal loops from fresh Hand #1.
      autoTargetHandCount.value = cycleSize
    } else {
      await startGame()
    }
    scheduleAutoTick(AUTO_AFTER_RESTART_DELAY_MS)
    return
  }

  await nextStep()
  scheduleAutoTick(AUTO_STEP_DELAY_MS)
}

const toggleAutoMode = () => {
  autoMode.value = !autoMode.value
  if (autoMode.value) {
    const currentHand = gameState.value?.hand_count ?? 0
    const cycleSize = autoCycleHands.value
    autoTargetHandCount.value = currentHand + cycleSize
    // First activation has no previous step to wait for, so kick off immediately.
    scheduleAutoTick(0)
    return
  }
  autoTargetHandCount.value = null
  clearAutoTimer()
}

onMounted(() => {
  engineGateway.init().then((state) => {
    gameState.value = state
  }).catch(() => {
    backendStatus.value = 'Offline'
  })
  engineGateway.startProbe()
  pollInterval = window.setInterval(fetchState, 1500) // Slightly slower poll to avoid overlapping
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  clearAutoTimer()
  engineGateway.stopProbe()
})

const fixedPositions = [
  { x: 0, y: 280 },      // 1
  { x: 380, y: 200 },    // 2
  { x: 520, y: 0 },      // 3
  { x: 380, y: -200 },   // 4
  { x: 0, y: -280 },     // 5
  { x: -380, y: -200 },  // 6
  { x: -520, y: 0 },     // 7
  { x: -380, y: 200 },   // 8
]

const getPlayerStyle = (index: number) => {
  const pos = fixedPositions[index] || { x: 0, y: 0 }
  const isCurrent = gameState.value?.current_player_idx === index
  return {
    transform: `translate(${pos.x}px, ${pos.y}px)`,
    zIndex: isCurrent ? 100 : 20 // Current player is ALWAYS on top
  }
}
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- Game Header Controls -->
    <div class="bg-gray-800 p-2 border-b border-gray-700 flex justify-between items-center px-4">
      <!-- Left side: Status -->
      <div class="flex items-center gap-2 text-sm">
        <span class="w-2 h-2 rounded-full" :class="backendStatus === 'Online' ? 'bg-green-500 animate-pulse' : 'bg-red-500'"></span>
        <span class="text-gray-300 font-medium">Engine: {{ backendStatus }}</span>
      </div>
      
      <!-- Right side: Controls -->
      <div class="flex items-center gap-3">
        <div class="flex gap-2 border-r border-gray-600 pr-3 mr-1">
             <button
               @click="resetCycle"
               :disabled="isProcessing"
               class="px-3 py-1 bg-red-700 rounded hover:bg-red-600 text-xs text-white transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
             >
               Full Restart
             </button>
             <button @click="startGame" class="px-3 py-1 bg-blue-700 rounded hover:bg-blue-600 text-xs text-white transition-colors font-medium">Restart Hand</button>
             <button 
               @click="nextStep" 
               :disabled="isProcessing || autoMode"
               class="px-3 py-1 bg-green-700 rounded hover:bg-green-600 text-xs text-white transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
             >
               <span v-if="isProcessing" class="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
               {{ isProcessing ? 'Processing...' : 'Next Step' }}
             </button>
             <button
               @click="toggleAutoMode"
               :disabled="isProcessing"
               class="px-3 py-1 rounded text-xs text-white transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
               :class="autoMode ? 'bg-amber-600 hover:bg-amber-500' : 'bg-gray-700 hover:bg-gray-600'"
             >
               Auto: {{ autoMode ? 'ON' : 'OFF' }}
             </button>
             <select
               v-model.number="autoCycleHands"
               :disabled="autoMode || isProcessing"
               class="px-2 py-1 rounded text-xs bg-gray-700 border border-gray-600 text-gray-200 focus:outline-none focus:border-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
             >
               <option :value="10">Auto 10</option>
               <option :value="20">Auto 20</option>
               <option :value="30">Auto 30</option>
             </select>
        </div>

        <button 
          @click="godMode = !godMode"
          class="px-3 py-1 rounded border transition-all duration-300 cursor-pointer text-xs font-medium"
          :class="godMode ? 'bg-purple-600 border-purple-500 text-white shadow-[0_0_10px_rgba(147,51,234,0.5)]' : 'bg-gray-700 border-gray-600 text-gray-400 hover:bg-gray-600'"
        >
          God Mode: {{ godMode ? 'ON' : 'OFF' }}
        </button>
      </div>
    </div>

    <!-- Main Arena -->
    <main class="flex-1 flex overflow-hidden relative" v-if="gameState">
      <div class="flex-1 p-8 flex flex-col items-center justify-center relative bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-gray-800 via-gray-900 to-gray-950">
        
        <div class="relative flex items-center justify-center">
            
            <!-- Poker Table -->
            <div class="relative w-[800px] h-[400px] bg-green-900/20 border-8 border-green-800/50 rounded-[200px] flex items-center justify-center shadow-[0_0_50px_rgba(20,83,45,0.3)] backdrop-blur-sm z-10">
              <!-- Community Cards -->
              <div class="flex gap-2 min-h-[96px]">
                 <div v-for="(card, i) in gameState.community_cards" :key="i"
                      class="w-16 h-24 bg-gray-100 rounded border border-gray-400 flex flex-col items-center justify-center shadow-md animate-in fade-in zoom-in duration-300"
                      :class="getCardColor(card.suit)">
                    <span class="text-lg font-bold">{{ card.rank }}</span>
                    <span class="text-xl leading-none">{{ getCardSymbol(card.suit) }}</span>
                 </div>
                 
                 <!-- Placeholders -->
                 <div v-if="gameState.community_cards.length < 3" class="w-16 h-24 bg-gray-700/50 rounded border border-gray-600/50 flex items-center justify-center text-xs text-gray-500 font-mono">FLOP</div>
                 <div v-if="gameState.community_cards.length < 3" class="w-16 h-24 bg-gray-700/50 rounded border border-gray-600/50 flex items-center justify-center text-xs text-gray-500 font-mono">FLOP</div>
                 <div v-if="gameState.community_cards.length < 3" class="w-16 h-24 bg-gray-700/50 rounded border border-gray-600/50 flex items-center justify-center text-xs text-gray-500 font-mono">FLOP</div>
                 <div v-if="gameState.community_cards.length < 4" class="w-16 h-24 bg-gray-700/50 rounded border border-gray-600/50 flex items-center justify-center text-xs text-gray-500 font-mono">TURN</div>
                 <div v-if="gameState.community_cards.length < 5" class="w-16 h-24 bg-gray-700/50 rounded border border-gray-600/50 flex items-center justify-center text-xs text-gray-500 font-mono">RIVER</div>
              </div>
              
              <div class="absolute bottom-16 text-yellow-500 font-mono text-xl font-bold tracking-widest drop-shadow-md">
                POT: ${{ gameState.pot_size }}
              </div>
              
              <div class="absolute top-24 text-green-300/50 font-mono text-sm uppercase tracking-widest">
                {{ gameState.stage }}
              </div>
            </div>

            <!-- Players -->
            <div 
                v-for="(player, index) in gameState.players" 
                :key="player.id"
                class="absolute w-24 h-24 rounded-full border-2 flex flex-col items-center justify-center shadow-lg transition-all z-20"
                :class="[
                    gameState.current_player_idx === index ? 'border-yellow-400 shadow-[0_0_15px_rgba(250,204,21,0.6)] bg-gray-700' : 'border-gray-600 bg-gray-800',
                    !player.is_active ? 'opacity-50 grayscale' : ''
                ]"
                :style="getPlayerStyle(index)"
            >
                <div class="w-10 h-10 rounded-full bg-indigo-500/30 mb-1 flex items-center justify-center text-xs text-indigo-300 font-bold relative">
                    {{ index + 1 }}
                     <div v-if="gameState.dealer_idx === index" class="absolute -top-1 -right-1 w-4 h-4 bg-white text-black text-[10px] rounded-full flex items-center justify-center border border-gray-400 font-bold">D</div>
                </div>
                <!-- Name & Chips -->
                <span class="text-xs font-bold text-gray-300">{{ player.name }}</span>
                <span class="text-xs text-yellow-500 font-mono">${{ player.chips }}</span>
                
                <!-- Last Action Badge -->
                <div v-if="player.last_action" 
                     class="absolute -bottom-8 px-2 py-0.5 rounded-full border text-[10px] font-bold shadow-md animate-in fade-in zoom-in duration-200 z-30"
                     :class="player.last_action.includes('Fold') ? 'bg-red-900/90 text-red-200 border-red-500/50' : 
                             player.last_action.includes('Raise') ? 'bg-yellow-900/90 text-yellow-200 border-yellow-500/50' :
                             'bg-blue-900/90 text-blue-200 border-blue-500/50'">
                    {{ player.last_action }}
                </div>

                <!-- Total Hand Bet Badge (Persistent) -->
                <div v-if="player.total_hand_bet > 0"
                     class="absolute -bottom-14 px-2 py-0.5 rounded-full bg-gray-800/90 border border-gray-600 text-[10px] text-green-400 font-mono shadow-sm z-20">
                     Σ ${{ player.total_hand_bet }}
                </div>

                <!-- Thought Bubble -->
                <div v-if="player.thought" 
                     :key="player.thought"
                     class="absolute -top-16 left-1/2 -translate-x-1/2 w-48 z-40"
                     :class="pinnedThoughtPlayerId === player.id ? 'thought-bubble-hold' : 'thought-bubble-animation'"
                     @mouseenter="pinnedThoughtPlayerId = player.id"
                     @mouseleave="pinnedThoughtPlayerId = null">
                    <div class="relative bg-white text-black p-2 rounded-xl text-[10px] leading-tight shadow-xl border border-gray-300">
                        {{ player.thought }}
                        <!-- Triangle -->
                        <div class="absolute -bottom-2 left-1/2 -translate-x-1/2 w-0 h-0 border-l-[6px] border-l-transparent border-t-[8px] border-t-white border-r-[6px] border-r-transparent"></div>
                    </div>
                </div>

                <!-- Cards -->
                <div class="absolute -right-16 top-1/2 -translate-y-1/2 flex gap-1 z-30" v-if="player.is_active && player.cards.length > 0">
                    <template v-if="godMode">
                       <div v-for="(card, ci) in player.cards" :key="ci" 
                            class="w-8 h-11 bg-gray-100 rounded border border-gray-400 shadow-sm flex flex-col items-center justify-center leading-none" 
                            :class="getCardColor(card.suit)">
                          <span class="text-xs font-bold">{{ card.rank }}</span>
                          <span class="text-[10px]">{{ getCardSymbol(card.suit) }}</span>
                       </div>
                    </template>
                    <template v-else>
                       <div class="w-8 h-11 bg-blue-900 rounded border border-blue-700 shadow-sm bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div>
                       <div class="w-8 h-11 bg-blue-900 rounded border border-blue-700 shadow-sm bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]"></div>
                    </template>
                </div>
            </div>

        </div>

      </div>

      <!-- Sidebar -->
      <aside class="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
        <div class="p-3 border-b border-gray-700 font-bold text-gray-400 text-xs uppercase tracking-wider">
          Game Log
        </div>
        <div class="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-2 text-gray-300 scrollbar-thin scrollbar-thumb-gray-600">
           <p><span class="text-blue-400">[System]</span> Connected to game engine.</p>
           
           <!-- Logs -->
           <p v-for="(log, i) in gameState.logs" :key="i" 
              class="pl-2 border-l-2"
              :class="log.includes('---') ? 'text-green-400 font-bold border-transparent mt-4 mb-2' : 'text-gray-300 border-gray-600'">
               {{ log }}
           </p>

           <p v-if="gameState.winners.length > 0"><span class="text-yellow-400">[Win]</span> Players {{ gameState.winners }} won the pot.</p>
        </div>
      </aside>
    </main>
    
    <div v-else class="flex-1 flex items-center justify-center">
        <div class="text-xl text-gray-500 animate-pulse">Connecting to Game Engine...</div>
    </div>
  </div>
</template>

<style scoped>
@keyframes thought-pop-fade {
  0% { 
    opacity: 0; 
    transform: translate(-50%, 15px) scale(0.8); 
  }
  15% { 
    opacity: 1; 
    transform: translate(-50%, 0) scale(1); 
  }
  80% { 
    opacity: 1; 
    transform: translate(-50%, 0) scale(1); 
  }
  100% { 
    opacity: 0; 
    transform: translate(-50%, -10px) scale(0.95); 
  }
}

.thought-bubble-animation {
  animation: thought-pop-fade 2s forwards;
}

.thought-bubble-hold {
  animation: none;
  opacity: 1;
  transform: translate(-50%, 0) scale(1);
}
</style>
