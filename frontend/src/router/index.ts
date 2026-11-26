import { createRouter, createWebHistory } from 'vue-router'
import ConversationView from '../views/ConversationView.vue'
import CorrectionsView from '../views/CorrectionsView.vue'
import HistoryView from '../views/HistoryView.vue'
import HomeView from '../views/HomeView.vue'
import PatternDrillView from '../views/PatternDrillView.vue'
import PatternsView from '../views/PatternsView.vue'
import PracticeView from '../views/PracticeView.vue'
import SettingsView from '../views/SettingsView.vue'
import VideosView from '../views/VideosView.vue'
import VideoView from '../views/VideoView.vue'
import WordsView from '../views/WordsView.vue'

const idProp = (route: { params: Record<string, string | string[]> }) => ({ id: Number(route.params.id) })

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/topics/:id(\\d+)', name: 'practice', component: PracticeView, props: idProp },
    { path: '/words', name: 'words', component: WordsView },
    { path: '/history', name: 'history', component: HistoryView },
    { path: '/history/:id(\\d+)', name: 'conversation', component: ConversationView, props: idProp },
    { path: '/patterns', name: 'patterns', component: PatternsView },
    { path: '/patterns/:id', name: 'pattern', component: PatternDrillView, props: true },
    { path: '/videos', name: 'videos', component: VideosView },
    { path: '/videos/:id(\\d+)', name: 'video', component: VideoView, props: idProp },
    { path: '/corrections', name: 'corrections', component: CorrectionsView },
    { path: '/settings', name: 'settings', component: SettingsView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
