<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { AgentRuntimeConfig, GameState, LLMProfileInfo, Player } from '../types'

const players = ref<Player[]>([])
const agents = ref<AgentRuntimeConfig[]>([])
const llmProfiles = ref<LLMProfileInfo[]>([])
const draftAgentConfig = ref<Record<number, { agent_type: string; profile: string }>>({})
const loading = ref(true)
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

const fetchState = async () => {
  try {
    const res = await fetch(apiUrl('/state'))
    const data: GameState = await res.json()
    players.value = data.players
    for (const p of data.players) {
      if (!draftAgentConfig.value[p.id]) {
        draftAgentConfig.value[p.id] = { agent_type: 'random', profile: '' }
      }
    }
    loading.value = false
  } catch (e) {
    console.error(e)
  }
}

const ensureDraftConfig = (playerId: number) => {
  if (!draftAgentConfig.value[playerId]) {
    draftAgentConfig.value[playerId] = { agent_type: 'random', profile: '' }
  }
  return draftAgentConfig.value[playerId]
}

const fetchAgentConfigs = async () => {
  try {
    const res = await fetch(apiUrl('/config/agents'))
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
  try {
    const res = await fetch(`${API_BASE_URL}/config/llm_profiles`)
    if (!res.ok) return
    const data = await res.json()
    llmProfiles.value = (data.profiles || []) as LLMProfileInfo[]
  } catch (e) {
    console.error(e)
  }
}

const updateAgent = async (player: Player) => {
  const draft = draftAgentConfig.value[player.id]
  if (!draft) return
  try {
    const payload = {
      player_id: player.id,
      agent_type: draft.agent_type,
      profile: draft.agent_type === 'llm' && draft.profile.trim() ? draft.profile.trim() : null
    }
    const res = await fetch(apiUrl('/config/agent'), {
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
    try {
        const res = await fetch(apiUrl('/config/persona'), {
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
    fetchState()
    fetchAgentConfigs()
    fetchProfiles()
})
</script>

<template>
  <div class="h-full p-8 overflow-y-auto">
    <h2 class="text-2xl font-bold mb-6 text-green-400">📊 Stats & Configuration</h2>
    
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
