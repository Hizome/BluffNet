<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { createEngineGateway } from '../lib/engineGateway'
import type { AgentRuntimeConfig, GameState, LLMProfileInfo, Player } from '../types'

const players = ref<Player[]>([])
const agents = ref<AgentRuntimeConfig[]>([])
const llmProfiles = ref<LLMProfileInfo[]>([])
const draftAgentConfig = ref<Record<number, { agent_type: string; profile: string }>>({})
const loading = ref(true)
const backendStatus = ref('Connecting...')
const remoteConfigAvailable = ref(false)
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
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
const apiUrl = (path: string) => `${API_BASE_URL}${path}?table_id=${encodeURIComponent(tableId)}`
const engineGateway = createEngineGateway({
  tableId,
  onModeChange: (mode) => {
    if (mode === 'remote') {
      backendStatus.value = 'Cloud'
      remoteConfigAvailable.value = true
      fetchAgentConfigs()
      fetchProfiles()
      return
    }
    if (mode === 'local') {
      backendStatus.value = 'Local fallback'
      remoteConfigAvailable.value = false
      return
    }
    backendStatus.value = 'Connecting...'
    remoteConfigAvailable.value = false
  },
})

const fetchWithTimeout = async (input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = 5000) => {
  const ctrl = new AbortController()
  const t = window.setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    return await fetch(input, { ...init, signal: ctrl.signal })
  } finally {
    clearTimeout(t)
  }
}

const fetchState = async () => {
  try {
    const data: GameState = await engineGateway.getState()
    players.value = data.players
    for (const p of data.players) {
      if (!draftAgentConfig.value[p.id]) {
        draftAgentConfig.value[p.id] = { agent_type: 'random', profile: '' }
      }
    }
    loading.value = false
    const mode = engineGateway.getMode()
    backendStatus.value = mode === 'remote' ? 'Cloud' : mode === 'local' ? 'Local fallback' : 'Connecting...'
  } catch (e) {
    console.error(e)
    backendStatus.value = 'Offline'
  }
}

const ensureDraftConfig = (playerId: number) => {
  if (!draftAgentConfig.value[playerId]) {
    draftAgentConfig.value[playerId] = { agent_type: 'random', profile: '' }
  }
  return draftAgentConfig.value[playerId]
}

const fetchAgentConfigs = async () => {
  if (!remoteConfigAvailable.value) return
  try {
    const res = await fetchWithTimeout(apiUrl('/config/agents'))
    if (!res.ok) return
    const data = await res.json()
    agents.value = (data.agents || []) as AgentRuntimeConfig[]
    for (const a of agents.value) {
      draftAgentConfig.value[a.player_id] = {
        agent_type: a.agent_type,
        profile: a.profile || ''
      }
    }
  } catch (e) {
    console.error(e)
  }
}

const fetchProfiles = async () => {
  if (!remoteConfigAvailable.value) return
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}/config/llm_profiles`)
    if (!res.ok) return
    const data = await res.json()
    llmProfiles.value = (data.profiles || []) as LLMProfileInfo[]
  } catch (e) {
    console.error(e)
  }
}

const updateAgent = async (player: Player) => {
  if (!remoteConfigAvailable.value) {
    alert('Cloud backend unavailable. Agent config is disabled in local fallback mode.')
    return
  }
  const draft = draftAgentConfig.value[player.id]
  if (!draft) return
  try {
    const payload = {
      player_id: player.id,
      agent_type: draft.agent_type,
      profile: draft.agent_type === 'llm' && draft.profile.trim() ? draft.profile.trim() : null
    }
    const res = await fetchWithTimeout(apiUrl('/config/agent'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      alert('Failed to update agent config')
      return
    }
    await fetchAgentConfigs()
    alert(`Updated Agent ${player.id + 1} config`)
  } catch (e) {
    alert('Error updating agent config')
  }
}

const updatePersona = async (player: Player) => {
    if (!remoteConfigAvailable.value) {
        alert('Cloud backend unavailable. Persona config is disabled in local fallback mode.')
        return
    }
    try {
        const res = await fetchWithTimeout(apiUrl('/config/persona'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_id: player.id, persona: player.persona })
        })
        if (!res.ok) alert("Failed to update persona")
        else alert(`Updated Agent ${player.id + 1} Persona`)
    } catch (e) {
        alert("Error updating persona")
    }
}

onMounted(() => {
    engineGateway.init().then((state) => {
      players.value = state.players
      loading.value = false
    }).catch(() => {
      backendStatus.value = 'Offline'
    })
    engineGateway.startProbe()
    fetchState()
    pollInterval = window.setInterval(fetchState, 2000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  engineGateway.stopProbe()
})
</script>

<template>
  <div class="h-full p-8 overflow-y-auto">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-2xl font-bold text-green-400">📊 Stats & Configuration</h2>
      <div class="text-xs px-2 py-1 rounded border border-gray-600 text-gray-300">
        Engine: {{ backendStatus }}
      </div>
    </div>
    <div v-if="!remoteConfigAvailable" class="mb-6 rounded border border-amber-500/50 bg-amber-900/20 px-3 py-2 text-xs text-amber-200">
      Cloud backend unavailable. Scoreboard works in local fallback mode, but agent/persona configuration is disabled until cloud reconnects.
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <!-- Scoreboard -->
        <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 class="text-lg font-bold text-gray-300 mb-4 border-b border-gray-600 pb-2">Scoreboard</h3>
            <table class="w-full text-left text-sm">
                <thead>
                    <tr class="text-gray-500 uppercase tracking-wider">
                        <th class="pb-2">Player</th>
                        <th class="pb-2">Chips</th>
                        <th class="pb-2">Wins</th>
                        <th class="pb-2">Hands Played</th>
                        <th class="pb-2">Win Rate</th>
                    </tr>
                </thead>
                <tbody class="text-gray-300">
                    <tr v-for="p in players" :key="p.id" class="border-b border-gray-700 last:border-0 hover:bg-gray-700/50">
                        <td class="py-3 font-bold text-indigo-400">{{ p.name }}</td>
                        <td class="py-3 font-mono text-yellow-500">${{ p.chips }}</td>
                        <td class="py-3">{{ p.stats?.wins || 0 }}</td>
                        <td class="py-3">{{ p.stats?.hands_played || 0 }}</td>
                        <td class="py-3">
                            {{ p.stats?.hands_played ? ((p.stats.wins / p.stats.hands_played) * 100).toFixed(1) + '%' : '0%' }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Configuration -->
        <div class="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 class="text-lg font-bold text-gray-300 mb-4 border-b border-gray-600 pb-2">Agent Configuration</h3>
            <div class="space-y-4">
                <div v-for="p in players" :key="p.id" class="flex flex-col gap-1">
                    <label class="text-xs text-gray-500 uppercase font-bold">{{ p.name }} Agent Type / Profile</label>
                    <div class="grid grid-cols-12 gap-2">
                        <select
                          v-model="ensureDraftConfig(p.id).agent_type"
                          class="col-span-4 bg-gray-900 border border-gray-600 rounded px-2 py-2 text-sm focus:border-green-500 focus:outline-none transition-colors"
                        >
                          <option value="llm">llm</option>
                          <option value="random">random</option>
                          <option value="call_station">call_station</option>
                        </select>
                        <input
                          v-model="ensureDraftConfig(p.id).profile"
                          type="text"
                          list="llm-profile-options"
                          :disabled="ensureDraftConfig(p.id).agent_type !== 'llm'"
                          placeholder="default / AI1 / GEMINI..."
                          class="col-span-6 bg-gray-900 border border-gray-600 rounded px-3 py-2 text-sm focus:border-green-500 focus:outline-none transition-colors disabled:opacity-50"
                        />
                        <button @click="updateAgent(p)" class="col-span-2 px-3 py-1 bg-gray-700 hover:bg-green-600 text-xs rounded transition-colors text-white">Save</button>
                    </div>
                    <div class="text-[11px] text-gray-500">
                      当前:
                      <span class="text-gray-300">{{ agents.find(a => a.player_id === p.id)?.agent_type || 'unknown' }}</span>
                      <template v-if="agents.find(a => a.player_id === p.id)?.profile">
                        /
                        <span class="text-gray-300">{{ agents.find(a => a.player_id === p.id)?.profile }}</span>
                      </template>
                      <template v-if="agents.find(a => a.player_id === p.id)?.llm">
                        |
                        <span :class="agents.find(a => a.player_id === p.id)?.llm?.has_api_key ? 'text-green-400' : 'text-red-400'">
                          key: {{ agents.find(a => a.player_id === p.id)?.llm?.has_api_key ? 'yes' : 'no' }}
                        </span>
                      </template>
                    </div>
                    <label class="text-xs text-gray-500 uppercase font-bold mt-1">{{ p.name }} Persona / Prompt</label>
                    <div class="flex gap-2">
                        <input v-model="p.persona" type="text" class="flex-1 bg-gray-900 border border-gray-600 rounded px-3 py-2 text-sm focus:border-green-500 focus:outline-none transition-colors" />
                        <button @click="updatePersona(p)" class="px-3 py-1 bg-gray-700 hover:bg-green-600 text-xs rounded transition-colors text-white">Save</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <datalist id="llm-profile-options">
      <option v-for="profile in llmProfiles" :key="profile.profile" :value="profile.profile" />
    </datalist>
  </div>
</template>
