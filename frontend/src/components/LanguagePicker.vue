<script setup lang="ts">
import { ref } from 'vue'
import { languageName, t } from '../i18n'
import { useSettingsStore } from '../stores/settings'
import BrandMark from './BrandMark.vue'

// The first thing the app asks: which language to practise. Nothing is downloaded before.
const settings = useSettingsStore()
const choosing = ref<string | null>(null)

async function choose(code: string) {
  choosing.value = code
  await settings.chooseLanguage(code)
  choosing.value = null
}
</script>

<template>
  <main class="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-6 p-6">
    <header class="text-center">
      <BrandMark class="mx-auto size-14" />
      <h1 class="mt-4 font-display text-3xl font-extrabold">{{ t('picker.title') }}</h1>
      <p class="mt-2 text-base-content/70">
        {{ t('picker.intro') }}
      </p>
    </header>

    <div v-if="settings.error" role="alert" class="alert alert-error alert-soft">{{ settings.error }}</div>

    <ul class="grid gap-3 sm:grid-cols-2">
      <li v-for="l in settings.languages ?? []" :key="l.code">
        <button
          class="btn btn-lg h-auto w-full flex-col gap-0 border-base-300 bg-base-100 py-4"
          :class="choosing === l.code ? 'btn-primary' : ''"
          :disabled="choosing !== null"
          :lang="l.code"
          @click="choose(l.code)"
        >
          <span class="text-xl">{{ l.native }}</span>
          <span v-if="l.native !== languageName(l.code, l.name)" class="text-sm font-normal text-base-content/60">
            {{ languageName(l.code, l.name) }}
          </span>
        </button>
      </li>
    </ul>

    <p class="text-center text-sm text-base-content/60">
      {{ t('picker.note') }}
    </p>
  </main>
</template>
