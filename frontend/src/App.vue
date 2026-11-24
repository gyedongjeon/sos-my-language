<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BrandMark from './components/BrandMark.vue'
import ModelDownloads from './components/ModelDownloads.vue'
import { useModelsStore } from './stores/models'
import { useSettingsStore } from './stores/settings'

const settings = useSettingsStore()
const router = useRouter()
const LINK = 'hover:bg-neutral-content/10'
onMounted(async () => {
  // Fetch the speech models in the background, so they are there before the first recording.
  void useModelsStore().start()
  settings.load()
  await settings.loadLLM()
  // First launch: nothing works well without a model, so start on the setup page.
  if (settings.llm && !settings.llm.model) router.replace({ name: 'settings' })
})
</script>

<template>
  <div class="min-h-screen bg-base-200 text-base-content">
    <nav class="navbar bg-neutral text-neutral-content">
      <div class="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-2 px-2">
        <RouterLink class="flex items-center gap-2 px-2 font-display text-xl" to="/">
          <BrandMark class="size-7" />
          <span><span class="font-extrabold text-primary">SOS</span> <span class="font-medium">My English</span></span>
        </RouterLink>
        <ul class="menu menu-horizontal ml-auto gap-1 px-0">
          <li><RouterLink :class="LINK" to="/" exact-active-class="bg-primary text-primary-content hover:bg-primary">Conversation</RouterLink></li>
          <li><RouterLink :class="LINK" to="/patterns" active-class="bg-primary text-primary-content hover:bg-primary">Patterns</RouterLink></li>
          <li><RouterLink :class="LINK" to="/videos" active-class="bg-primary text-primary-content hover:bg-primary">Videos</RouterLink></li>
          <li><RouterLink :class="LINK" to="/corrections" active-class="bg-primary text-primary-content hover:bg-primary">Corrections</RouterLink></li>
          <li><RouterLink :class="LINK" to="/history" active-class="bg-primary text-primary-content hover:bg-primary">History</RouterLink></li>
          <li><RouterLink :class="LINK" to="/settings" active-class="bg-primary text-primary-content hover:bg-primary">Settings</RouterLink></li>
        </ul>
      </div>
    </nav>
    <ModelDownloads />
    <div v-if="settings.error" role="alert" class="alert alert-error alert-soft mx-auto mt-4 max-w-3xl">
      {{ settings.error }}
    </div>
    <div
      v-if="settings.llm && !settings.llm.model && $route.name !== 'settings'"
      role="alert"
      class="alert alert-warning alert-soft mx-auto mt-4 max-w-3xl"
    >
      <span>Add an AI model and API key so your conversation partner can reply and correct your English.</span>
      <RouterLink class="btn btn-sm btn-warning" to="/settings">Open Settings</RouterLink>
    </div>
    <RouterView />
  </div>
</template>
