<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import MorseSignal from '../components/MorseSignal.vue'
import { micProblem, useRecorder } from '../composables/useRecorder'
import { useSpeech } from '../composables/useSpeech'
import { source, useCorrectionsStore } from '../stores/corrections'

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
const shown = computed(() => store.items.filter((c) => showPracticed.value || c.practiced === 0 || store.results[c.id]))
const practiced = computed(() => store.items.length - store.remaining)
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
  if (!audio) error.value = 'Nothing was recorded. Try again.'
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
    <h1 class="text-2xl font-semibold">Corrections</h1>
    <p class="text-sm text-base-content/70">
      The fixes from your conversations, the sentences you got wrong in pattern practice, and the sentences of a video
      you did not say right after it. Listen to the better sentence, then say it yourself until it comes out right.
    </p>

    <div v-if="store.loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>
    <template v-else>
      <div v-if="error || store.error" role="alert" class="alert alert-error alert-soft mt-4">{{ error || store.error }}</div>

      <div v-if="!store.items.length && !store.error" class="card card-border mt-4 bg-base-100">
        <div class="card-body items-start">
          <p>No corrections yet. They appear here as you get them in a conversation, in pattern practice, or saying a video's sentences after it.</p>
          <RouterLink class="btn btn-primary btn-sm" :to="{ name: 'home' }">Pick a topic</RouterLink>
        </div>
      </div>

      <div v-else-if="store.items.length" class="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm">
        <span>
          <strong>{{ store.remaining }}</strong> to practise · {{ practiced }} said right
        </span>
        <label v-if="practiced" class="label cursor-pointer gap-2">
          <input v-model="showPracticed" type="checkbox" class="toggle toggle-sm" />
          Show the ones already said right
        </label>
      </div>

      <p v-if="store.items.length && !shown.length" class="mt-4 text-base-content/70">
        Everything here has been said right at least once.
      </p>

      <ul class="mt-3 grid gap-3">
        <li v-for="c in shown" :key="c.id" class="card card-border bg-base-100">
          <div class="card-body gap-2">
            <p v-if="c.prompt" class="text-sm text-base-content/70">{{ c.prompt }}</p>
            <p class="text-base-content/60 line-through">{{ c.original }}</p>
            <p class="text-lg font-medium text-success">{{ c.improved }}</p>
            <p class="text-sm text-base-content/70">{{ c.explanation }}</p>

            <div class="flex flex-wrap items-center gap-2">
              <button class="btn btn-sm" @click="speech.speak(c.improved)">Hear it</button>
              <button v-if="speaking === c.id" class="btn btn-error btn-sm" @click="stop">
                <span class="inline-block size-2 animate-pulse rounded-full bg-current"></span>
                Stop
              </button>
              <button v-else class="btn btn-primary btn-sm" :disabled="busy" @click="start(c.id)">Say it</button>
              <span v-if="store.checking === c.id" class="flex items-center gap-2 text-sm text-base-content/60">
                <MorseSignal animated /> Listening to what you said…
              </span>
              <span v-if="c.practiced" class="badge badge-success badge-soft">Said right ×{{ c.practiced }}</span>
              <RouterLink v-if="source(c)" class="link ml-auto text-xs text-base-content/60" :to="source(c)!">
                From “{{ c.title }}”
              </RouterLink>
              <span v-else class="ml-auto text-xs text-base-content/60">From “{{ c.title }}” (deleted)</span>
              <template v-if="confirming === c.id">
                <button class="btn btn-error btn-xs" @click="remove(c.id)">Remove for good</button>
                <button class="btn btn-ghost btn-xs" @click="confirming = null">Keep</button>
              </template>
              <button v-else class="btn btn-ghost btn-xs" :aria-label="`Remove the correction ${c.improved}`" @click="confirming = c.id">
                Remove
              </button>
            </div>

            <div v-if="store.results[c.id] && store.checking !== c.id && speaking !== c.id" class="text-sm" aria-live="polite">
              <p v-if="store.results[c.id].matched" class="font-medium text-success">That's it!</p>
              <template v-else>
                <p>
                  <span class="text-base-content/60">Heard:</span> {{ store.results[c.id].heard }}
                  <template v-if="store.results[c.id].missing.length">
                    <span class="text-base-content/60"> · missing:</span>
                    <strong class="text-primary"> {{ store.results[c.id].missing.join(', ') }}</strong>
                  </template>
                  <span v-else class="text-base-content/60"> · the words are there, but not in that order</span>
                </p>
                <button class="btn btn-ghost btn-xs mt-1" :disabled="busy" @click="store.countAnyway(c.id)">
                  I said it right — count it
                </button>
              </template>
            </div>
          </div>
        </li>
      </ul>
    </template>
  </main>
</template>
