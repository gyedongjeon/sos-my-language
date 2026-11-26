<script setup lang="ts">
import { onMounted, ref, watch, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import BrandMark from './components/BrandMark.vue'
import LanguagePicker from './components/LanguagePicker.vue'
import ModelDownloads from './components/ModelDownloads.vue'
import WordPopover from './components/WordPopover.vue'
import { t } from './i18n'
import { useModelsStore } from './stores/models'
import { useSettingsStore } from './stores/settings'

const settings = useSettingsStore()
const router = useRouter()
const LINK = 'hover:bg-neutral-content/10'
// The chosen theme, or none to let daisyUI follow the system's light or dark mode.
watchEffect(() => {
  if (settings.theme) document.documentElement.dataset.theme = settings.theme
  else delete document.documentElement.dataset.theme
})
// Bumped when the learner goes over to another language from the navigation bar, so the page
// that is open starts again with that language's topics, videos, or patterns.
const restarted = ref(0)

async function switchLanguage(code: string) {
  if (!(await settings.chooseLanguage(code))) return
  restarted.value++
  // The page of one conversation, video, or pattern belongs to the language left behind.
  if (router.currentRoute.value.params.id !== undefined) void router.push({ name: 'home' })
}

// Once a language is chosen (on the first start: in the picker), the rest of the setup follows.
watch(
  () => settings.learning !== null,
  async (chosen) => {
    if (!chosen) return
    // Fetch the speech models in the background, so they are there before the first recording.
    void useModelsStore().start()
    await settings.loadLLM()
    // First launch: nothing works well without a model, so start on the setup page.
    if (settings.llm && !settings.llm.model) router.replace({ name: 'settings' })
  },
)

// The learner's own language comes first: the question that follows is asked in it.
onMounted(async () => {
  await settings.load()
  await settings.loadLanguages()
})
</script>

<template>
  <div class="min-h-screen bg-base-200 text-base-content">
    <!-- The first start: nothing else is shown, or downloaded, before a language is chosen. -->
    <LanguagePicker v-if="settings.languages && !settings.learning" />
    <template v-else-if="settings.learning">
      <nav class="navbar bg-neutral text-neutral-content">
        <div class="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-2 px-2">
          <RouterLink class="flex items-center gap-2 px-2 font-display text-xl" to="/">
            <BrandMark class="size-7" />
            <span><span class="font-extrabold text-primary">SOS</span> <span class="font-medium">My Language</span></span>
          </RouterLink>
          <select
            class="select select-sm w-auto border-neutral-content/30 bg-neutral text-neutral-content"
            :aria-label="t('nav.practise')"
            :value="settings.learning.code"
            @change="switchLanguage(($event.target as HTMLSelectElement).value)"
          >
            <option v-for="l in settings.languages ?? []" :key="l.code" :value="l.code">{{ l.native }}</option>
          </select>
          <ul class="menu menu-horizontal ml-auto gap-1 px-0">
            <li><RouterLink :class="LINK" to="/" exact-active-class="bg-primary text-primary-content hover:bg-primary">{{ t('nav.conversation') }}</RouterLink></li>
            <li><RouterLink :class="LINK" to="/patterns" active-class="bg-primary text-primary-content hover:bg-primary">{{ t('nav.patterns') }}</RouterLink></li>
            <li><RouterLink :class="LINK" to="/videos" active-class="bg-primary text-primary-content hover:bg-primary">{{ t('nav.videos') }}</RouterLink></li>
            <li><RouterLink :class="LINK" to="/corrections" active-class="bg-primary text-primary-content hover:bg-primary">{{ t('nav.corrections') }}</RouterLink></li>
            <li><RouterLink :class="LINK" to="/history" active-class="bg-primary text-primary-content hover:bg-primary">{{ t('nav.history') }}</RouterLink></li>
            <li><RouterLink :class="LINK" to="/settings" active-class="bg-primary text-primary-content hover:bg-primary">{{ t('nav.settings') }}</RouterLink></li>
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
        <span>{{ t('app.needModel', { language: settings.learningName }) }}</span>
        <RouterLink class="btn btn-sm btn-warning" to="/settings">{{ t('app.openSettings') }}</RouterLink>
      </div>
      <RouterView :key="restarted" />
      <WordPopover />
    </template>
    <div v-else-if="settings.error" role="alert" class="alert alert-error alert-soft mx-auto mt-4 max-w-3xl">
      {{ settings.error }}
    </div>
  </div>
</template>
