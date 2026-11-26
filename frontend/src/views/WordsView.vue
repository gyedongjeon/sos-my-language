<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import MarkedText from '../components/MarkedText.vue'
import MorseSignal from '../components/MorseSignal.vue'
import { useSpeech } from '../composables/useSpeech'
import { t } from '../i18n'
import type { SavedWord } from '../types'

// The words the learner saved, the newest first, each with the sentence it came from.
const words = ref<SavedWord[]>([])
const loading = ref(true)
const error = ref('')
const speech = useSpeech()

async function remove(id: number) {
  error.value = ''
  try {
    await api(`/words/${id}`, { method: 'DELETE' })
    words.value = words.value.filter((w) => w.id !== id)
  } catch (e) {
    error.value = (e as Error).message
  }
}

onMounted(async () => {
  try {
    words.value = await api<SavedWord[]>('/words')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="mx-auto max-w-3xl p-4 sm:p-6">
    <h1 class="text-2xl font-semibold">{{ t('nav.words') }}</h1>
    <p class="text-sm text-base-content/70">{{ t('words.intro') }}</p>

    <div v-if="loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>
    <template v-else>
      <div v-if="error" role="alert" class="alert alert-error alert-soft mt-4">{{ error }}</div>

      <div v-if="!words.length && !error" class="card card-border mt-4 bg-base-100">
        <div class="card-body">
          <p>{{ t('words.none') }}</p>
        </div>
      </div>

      <ul class="mt-4 grid gap-3">
        <li v-for="w in words" :key="w.id" class="card card-border bg-base-100">
          <div class="card-body gap-1 p-4">
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="text-lg font-semibold">{{ w.headword }}</h2>
              <span v-if="w.phrase && w.phrase !== w.lemma" class="text-sm text-base-content/60">{{ w.lemma }}</span>
              <span v-if="w.part_of_speech" class="badge badge-ghost badge-sm">{{ w.part_of_speech }}</span>
              <button class="btn btn-ghost btn-xs" @click="speech.speak(w.phrase || w.word)">{{ t('common.hearIt') }}</button>
              <button class="btn btn-ghost btn-xs ml-auto" :aria-label="t('words.remove', { word: w.headword })" @click="remove(w.id)">
                {{ t('common.delete') }}
              </button>
            </div>
            <p class="font-medium">{{ w.meaning }}</p>
            <MarkedText tag="p" class="text-sm italic text-base-content/70" :text="w.sentence" :part="w.word" whole />
            <MarkedText v-if="w.translation" tag="p" class="text-sm text-base-content/60" :text="w.translation" :part="w.in_translation" />
          </div>
        </li>
      </ul>
    </template>
  </main>
</template>
