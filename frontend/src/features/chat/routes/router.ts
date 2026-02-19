import type { RouteRecordRaw } from 'vue-router'
import ChatView from '@/features/chat/views/ChatView.vue'

export default [
  {
    path: '/',
    name: 'chat',
    component: ChatView,
    meta: { title: 'Chat' },
  },
] as RouteRecordRaw[]
