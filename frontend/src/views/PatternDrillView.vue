<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MorseSignal from '../components/MorseSignal.vue'
import { micProblem, useRecorder } from '../composables/useRecorder'
import { useSpeech } from '../composables/useSpeech'
import { useDrillStore } from '../stores/drill'
import { usePatternsStore } from '../stores/patterns'
import { useSettingsStore } from '../stores/settings'
import { t, tc } from '../i18n'

const settings = useSettingsStore()

// One round of a sentence pattern: each sentence is shown in the learner's language and said in the language practised.
const props = defineProps<{ id: string }>()

const patterns = usePatternsStore()
const drill = useDrillStore()
const speech = useSpeech()
const recorder = useRecorder()

const error = ref('') // Problems of this page: the microphone.
const pattern = computed(() => patterns.byId(props.id))
const busy = computed(() => drill.phase === 'transcribing' || drill.phase === 'checking')

async function begin() {
  speech.stop()
  recorder.release()
  error.value = ''
  await patterns.ensureLoaded()
  if (pattern.value) await drill.start(pattern.value)
}

async function startSpeaking() {
  error.value = ''
  drill.error = ''
  speech.stop()
  try {
    await recorder.start()
  } catch (e) {
    error.value = micProblem(e)
  }
}

async function stopSpeaking() {
  const audio = await recorder.stop()
  if (!audio) {
    error.value = t('common.nothingRecorded')
    return
  }
  await drill.attempt(audio)
}

function next() {
  speech.stop()
  void drill.next()
}

watch(() => props.id, begin)
onMounted(begin)
onBeforeUnmount(() => {
  speech.stop()
  recorder.release()
})
</script>

<template>
  <main class="mx-auto max-w-3xl p-4 sm:p-6">
    <RouterLink class="link text-sm" :to="{ name: 'patterns' }">{{ t('drill.allPatterns') }}</RouterLink>

    <div v-if="patterns.loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>

    <template v-else-if="pattern">
      <header class="mt-2">
        <p class="text-sm font-medium text-primary">{{ tc(pattern.level) }}</p>
        <h1 class="text-2xl font-semibold">{{ pattern.pattern }}</h1>
        <p class="text-sm text-base-content/70">{{ drill.note || tc(pattern.use) }}</p>
        <p class="mt-2 flex flex-wrap items-center gap-2">
          <span class="font-medium">{{ pattern.example }}</span>
          <button class="btn btn-xs" @click="speech.speak(pattern.example)">{{ t('common.hearIt') }}</button>
        </p>
      </header>

      <div v-if="drill.phase === 'loading'" class="flex items-center gap-2 py-10 text-sm text-base-content/60">
        <MorseSignal animated /> {{ t('drill.writing') }}
      </div>

      <section v-else-if="drill.phase === 'done'" class="card card-border mt-4 bg-base-100" :aria-label="t('drill.result')">
        <div class="card-body items-start gap-3">
          <h2 class="card-title">{{ t('drill.score', { score: drill.score, total: drill.items.length }) }}</h2>
          <p v-if="drill.score === drill.items.length" class="text-success">{{ t('drill.perfect') }}</p>
          <p v-else class="text-base-content/70">{{ t('drill.another') }}</p>
          <div class="flex flex-wrap gap-2">
            <button class="btn btn-primary btn-sm" @click="begin">{{ t('drill.anotherRound') }}</button>
            <RouterLink class="btn btn-sm" :to="{ name: 'patterns' }">{{ t('drill.pickAnother') }}</RouterLink>
          </div>
        </div>
      </section>

      <section v-else-if="drill.current" class="card card-border mt-4 bg-base-100" :aria-label="t('drill.sentence')">
        <div class="card-body gap-3">
          <p class="text-sm text-base-content/60">{{ t('drill.progress', { n: drill.index + 1, total: drill.items.length }) }}</p>
          <p class="text-xl font-medium">{{ drill.current.prompt }}</p>

          <div v-if="busy" class="flex items-center gap-2 text-sm text-base-content/60">
            <MorseSignal animated />
            {{ drill.phase === 'transcribing' ? t('common.listening') : t('drill.checking') }}
          </div>

          <div v-else-if="drill.last" class="rounded-box bg-base-200 p-3 text-sm" aria-live="polite">
            <p v-if="drill.last.correct" class="font-medium text-success">{{ t('drill.right') }}</p>
            <p v-else-if="drill.last.heard" class="font-medium text-primary">{{ t('drill.notQuite') }}</p>
            <p v-if="drill.last.heard"><span class="text-base-content/60">{{ t('common.youSaid') }}</span> {{ drill.last.heard }}</p>
            <p class="mt-1 flex flex-wrap items-center gap-2">
              <span class="text-base font-medium text-success">{{ drill.last.improved }}</span>
              <button class="btn btn-xs" @click="speech.speak(drill.last.improved)">{{ t('common.hearIt') }}</button>
            </p>
            <p v-if="drill.last.explanation" class="mt-1 text-base-content/70">{{ drill.last.explanation }}</p>
            <p v-if="!drill.last.correct && drill.last.heard" class="mt-1 text-xs text-base-content/60">
              {{ t('drill.keptBefore') }}<RouterLink class="link" :to="{ name: 'corrections' }">{{ t('nav.corrections') }}</RouterLink
              >{{ t('drill.keptAfter') }}
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <button v-if="recorder.recording.value" class="btn btn-error" @click="stopSpeaking">
              <span class="inline-block size-3 animate-pulse rounded-full bg-current"></span>
              {{ t('common.stop') }}
            </button>
            <template v-else>
              <button class="btn" :class="drill.last ? '' : 'btn-primary'" :disabled="busy" @click="startSpeaking">
                {{ drill.last ? t('drill.sayAgain') : t('drill.sayIn', { language: settings.learningName }) }}
              </button>
              <button v-if="drill.last" class="btn btn-primary" :disabled="busy" @click="next">
                {{ drill.index + 1 < drill.items.length ? t('drill.nextSentence') : t('drill.finish') }}
              </button>
              <button v-else class="btn btn-ghost" :disabled="busy" @click="drill.reveal()">{{ t('drill.showAnswer') }}</button>
            </template>
          </div>
        </div>
      </section>

      <div v-if="error || drill.error" role="alert" class="alert alert-error alert-soft mt-4">
        {{ error || drill.error }}
        <button v-if="!drill.items.length && drill.phase === 'idle'" class="btn btn-sm" @click="begin">{{ t('common.tryAgain') }}</button>
      </div>
    </template>

    <div v-else role="alert" class="alert alert-error mt-4">{{ patterns.error || t('drill.notFound') }}</div>
  </main>
</template>
