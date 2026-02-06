import { createRouter, createWebHistory } from 'vue-router'
import GameView from '../views/GameView.vue'
import DashboardView from '../views/DashboardView.vue'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            name: 'game',
            component: GameView
        },
        {
            path: '/dashboard',
            name: 'dashboard',
            component: DashboardView
        }
    ]
})

export default router
