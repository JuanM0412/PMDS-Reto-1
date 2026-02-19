import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import chatRouter from '@/features/chat/routes/router'

const routes: RouteRecordRaw[] = [...chatRouter]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
