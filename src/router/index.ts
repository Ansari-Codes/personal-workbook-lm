import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/Pages/HomePage.vue'
import ProfileIndex from '@/Pages/Profile/Index.vue'
import WorkbooksPage from '@/Pages/Profile/WorkbooksPage.vue'
import APIKeysPage from '@/Pages/Profile/APIKeysPage.vue'
import CallersPage from '@/Pages/Profile/CallersPage.vue'
import ToolsPage from '@/Pages/Profile/ToolsPage.vue'
import WorkbookPage from '@/Pages/Workbook/Index.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    {
      path: '/profile/:name',
      component: ProfileIndex,
      props: (route) => ({ profileName: String(route.params.name ?? '') }),
      children: [
        { path: '', name: 'profile', component: WorkbooksPage },
        { path: 'apis', name: 'profile-apis', component: APIKeysPage },
        { path: 'callers', name: 'profile-callers', component: CallersPage },
        { path: 'tools', name: 'profile-tools', component: ToolsPage },
      ],
    },
    {
      path: '/profile/:name/workbook/:workbookName',
      name: 'workbook',
      component: WorkbookPage,
      props: (route) => ({
        profileName: String(route.params.name ?? ''),
        workbookName: String(route.params.workbookName ?? ''),
      }),
    },
  ],
})

export default router
