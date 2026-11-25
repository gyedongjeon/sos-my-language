<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import MorseSignal from '../components/MorseSignal.vue'
import { micProblem, useRecorder } from '../composables/useRecorder'
import { useSpeech } from '../composables/useSpeech'
import { source, useCorrectionsStore } from '../stores/corrections'
import { t, tc } from '../i18n'

// Every correction from the saved conversations, pattern practice, and shadowing, to practise by saying the better sentence aloud.
const store = useCorrectionsStore()
const speech = useSpeech()
const recorder = useRecorder()

const error = ref('') // Problems of this page: the microphone.
// The correction being recorded.
const speaking = ref<string | null>(null)
// The correction whose "Remove" was pressed once; removing takes a second press.
const confirming = ref<string | null>(null)
const showPracticed = ref(false)

// A correction said right during this visit stays where it is, so its result can be read.
const shown = computed(() => store.ofKind.filter((c) => showPracticed.value || c.practiced === 0 || store.results[c.id]))
const practiced = computed(() => store.ofKind.length - store.remaining)
// Better expressions from conversations and patterns, apart from sentences of videos not said right after them.
const TABS = [
  { kind: 'expression', label: 'corrections.expressions', none: 'corrections.noExpressions' },
  { kind: 'shadowing', label: 'corrections.shadowing', none: 'corrections.noShadowing' },
] as const
const tab = computed(() => TABS.find((tab) => tab.kind === store.kind)!)
const busy = computed(() => speaking.value !== null || store.checking !== null)

async function remove(id: string) {
  await store.remove(id)
  confirming.value = null
}

async function start(id: string) {
  error.value = ''
  store.error = ''
  speech.stop()
  try {
    await recorder.start()
    speaking.value = id
  } catch (e) {
    error.value = micProblem(e)
  }
}

async function stop() {
  const id = speaking.value
  const audio = await recorder.stop()
  speaking.value = null
  if (id === null) return
  if (!audio) error.value = t('common.nothingRecorded')
  else await store.attempt(id, audio)
}

onMounted(() => {
  store.results = {}
  void store.load()
})
onBeforeUnmount(() => {
  speech.stop()
  recorder.release()
})
</script>

<template>
  <main class="mx-auto max-w-3xl p-4 sm:p-6">
    <h1 class="text-2xl font-semibold">{{ t('nav.corrections') }}</h1>
    <p class="text-sm text-base-content/70">
      {{ t('corrections.intro') }}
    </p>

    <div v-if="store.loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>
    <template v-else>
      <div v-if="error || store.error" role="alert" class="alert alert-error alert-soft mt-4">{{ error || store.error }}</div>

      <div v-if="!store.items.length && !store.error" class="card card-border mt-4 bg-base-100">
        <div class="card-body items-start">
          <p>{{ t('corrections.none') }}</p>
          <RouterLink class="btn btn-primary btn-sm" :to="{ name: 'home' }">{{ t('common.pickTopic') }}</RouterLink>
        </div>
      </div>

      <div v-if="store.items.length" class="mt-4 flex flex-wrap gap-2" role="tablist" :aria-label="t('nav.corrections')">
        <button
          v-for="tab in TABS"
          :key="tab.kind"
          role="tab"
          :aria-selected="tab.kind === store.kind"
          class="btn btn-sm rounded-full"
          :class="tab.kind === store.kind ? 'btn-primary' : 'btn-ghost bg-base-100'"
          @click="store.kind = tab.kind"
        >
          {{ t(tab.label) }}
          <span v-if="store.left[tab.kind]" class="badge badge-sm">{{ store.left[tab.kind] }}</span>
        </button>
      </div>

      <p v-if="store.items.length && !store.ofKind.length" class="mt-4 text-base-content/70">
        {{ t(tab.none) }}
      </p>

      <div v-else-if="store.items.length" class="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm">
        <span>{{ t('corrections.counts', { remaining: store.remaining, practiced }) }}</span>
        <label v-if="practiced" class="label cursor-pointer gap-2">
          <input v-model="showPracticed" type="checkbox" class="toggle toggle-sm" />
          {{ t('corrections.showPracticed') }}
        </label>
      </div>

      <p v-if="store.ofKind.length && !shown.length" class="mt-4 text-base-content/70">
        {{ t('corrections.allDone') }}
      </p>

      <ul class="mt-3 grid gap-3">
        <li v-for="c in shown" :key="c.id" class="card card-border bg-base-100">
          <div class="card-body gap-2">
            <template v-if="c.kind === 'shadowing'">
              <!-- What was heard is not a wrong sentence, so it is not crossed out. -->
              <p class="text-lg font-medium">{{ c.improved }}</p>
              <p class="text-sm">
                <span class="text-base-content/60">{{ t('corrections.heard') }}</span> {{ c.original }}
              </p>
              <p class="text-sm text-base-content/70">{{ c.explanation }}</p>
            </template>
            <template v-else>
              <p v-if="c.prompt" class="text-sm text-base-content/70">{{ c.prompt }}</p>
              <p class="text-base-content/60 line-through">{{ c.original }}</p>
              <p class="text-lg font-medium text-success">{{ c.improved }}</p>
              <p class="text-sm text-base-content/70">{{ c.explanation }}</p>
            </template>

            <div class="flex flex-wrap items-center gap-2">
              <button class="btn btn-sm" @click="speech.speak(c.improved)">{{ t('common.hearIt') }}</button>
              <button v-if="speaking === c.id" class="btn btn-error btn-sm" @click="stop">
                <span class="inline-block size-2 animate-pulse rounded-full bg-current"></span>
                {{ t('common.stop') }}
              </button>
              <button v-else class="btn btn-primary btn-sm" :disabled="busy" @click="start(c.id)">{{ t('corrections.sayIt') }}</button>
              <span v-if="store.checking === c.id" class="flex items-center gap-2 text-sm text-base-content/60">
                <MorseSignal animated /> {{ t('common.listening') }}
              </span>
              <span v-if="c.practiced" class="badge badge-success badge-soft">{{ t('corrections.saidRight', { n: c.practiced }) }}</span>
              <RouterLink v-if="source(c)" class="link ml-auto text-xs text-base-content/60" :to="source(c)!">
                {{ t('corrections.from', { title: tc(c.title) }) }}
              </RouterLink>
              <span v-else class="ml-auto text-xs text-base-content/60">{{ t('corrections.fromDeleted', { title: tc(c.title) }) }}</span>
              <template v-if="confirming === c.id">
                <button class="btn btn-error btn-xs" @click="remove(c.id)">{{ t('corrections.removeForGood') }}</button>
                <button class="btn btn-ghost btn-xs" @click="confirming = null">{{ t('common.keep') }}</button>
              </template>
              <button v-else class="btn btn-ghost btn-xs" :aria-label="t('corrections.removeOne', { sentence: c.improved })" @click="confirming = c.id">
                {{ t('corrections.remove') }}
              </button>
            </div>

            <div v-if="store.results[c.id] && store.checking !== c.id && speaking !== c.id" class="text-sm" aria-live="polite">
              <p v-if="store.results[c.id].matched" class="font-medium text-success">{{ t('corrections.thatsIt') }}</p>
              <template v-else>
                <p>
                  <span class="text-base-content/60">{{ t('corrections.heard') }}</span> {{ store.results[c.id].heard }}
                  <template v-if="store.results[c.id].missing.length">
                    <span class="text-base-content/60">{{ t('corrections.missing') }}</span>
                    <strong class="text-primary"> {{ store.results[c.id].missing.join(', ') }}</strong>
                  </template>
                  <span v-else class="text-base-content/60">{{ t('corrections.wrongOrder') }}</span>
                </p>
                <button class="btn btn-ghost btn-xs mt-1" :disabled="busy" @click="store.countAnyway(c.id)">
                  {{ t('corrections.countIt') }}
                </button>
              </template>
            </div>
          </div>
        </li>
      </ul>
    </template>
  </main>
</template>
