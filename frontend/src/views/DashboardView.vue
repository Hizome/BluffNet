<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { GameState, Player } from '../types'

const players = ref<Player[]>([])
const loading = ref(true)

const fetchState = async () => {
  try {
    const res = await fetch('http://localhost:8000/state')
    const data: GameState = await res.json()
    players.value = data.players
    loading.value = false
  } catch (e) {
    console.error(e)
  }
}

const updatePersona = async (player: Player) => {
    try {
        const res = await fetch('http://localhost:8000/config/persona', {
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
                    <label class="text-xs text-gray-500 uppercase font-bold">{{ p.name }} Persona / Prompt</label>
                    <div class="flex gap-2">
                        <input v-model="p.persona" type="text" class="flex-1 bg-gray-900 border border-gray-600 rounded px-3 py-2 text-sm focus:border-green-500 focus:outline-none transition-colors" />
                        <button @click="updatePersona(p)" class="px-3 py-1 bg-gray-700 hover:bg-green-600 text-xs rounded transition-colors text-white">Save</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
  </div>
</template>
