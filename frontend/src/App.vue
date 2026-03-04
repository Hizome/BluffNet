<script setup lang="ts">
import { onMounted } from 'vue'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

onMounted(() => {
  // Non-blocking warmup ping to reduce first meaningful backend request latency.
  fetch(`${API_BASE_URL}/status?table_id=default`).catch(() => {})
})
</script>

<template>
  <div class="h-screen bg-gray-900 text-white font-sans flex flex-col">
    <!-- Global Header -->
    <header class="bg-gray-800 p-4 border-b border-gray-700 flex justify-between items-center bg-opacity-80 backdrop-blur-md z-50">
      <div class="flex items-center gap-6">
          <h1 class="text-xl font-bold tracking-wider text-green-400">🃏 BluffNet <span class="text-xs text-gray-400 font-normal">Alpha</span></h1>
          
          <!-- Navigation -->
          <nav class="flex gap-4 text-sm font-medium">
              <router-link to="/" class="text-gray-400 hover:text-white transition-colors" active-class="text-green-400">
                  Game
              </router-link>
              <router-link to="/dashboard" class="text-gray-400 hover:text-white transition-colors" active-class="text-green-400">
                  Dashboard
              </router-link>
          </nav>
      </div>

    </header>

    <!-- Page Content -->
    <div class="flex-1 overflow-hidden">
        <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
                <component :is="Component" />
            </transition>
        </router-view>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
