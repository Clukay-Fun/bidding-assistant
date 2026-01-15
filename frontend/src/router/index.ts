import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/chat',
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { title: '智能对话', icon: 'ChatDotRound' },
  },
  {
    path: '/performances',
    name: 'Performances',
    component: () => import('@/views/PerformanceView.vue'),
    meta: { title: '业绩管理', icon: 'Document' },
  },
  {
    path: '/enterprises',
    name: 'Enterprises',
    component: () => import('@/views/EnterpriseView.vue'),
    meta: { title: '企业管理', icon: 'OfficeBuilding' },
  },
  {
    path: '/lawyers',
    name: 'Lawyers',
    component: () => import('@/views/LawyerView.vue'),
    meta: { title: '律师管理', icon: 'User' },
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('@/views/UploadView.vue'),
    meta: { title: '合同上传', icon: 'Upload' },
  },
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：设置页面标题
router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || '招投标助手'} - 招投标助手`
  next()
})

export default router