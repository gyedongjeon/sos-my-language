<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import CorrectionCard from '../components/CorrectionCard.vue'
import DeliveryNote from '../components/DeliveryNote.vue'
import MorseSignal from '../components/MorseSignal.vue'
import ReviewCard from '../components/ReviewCard.vue'
import { micProblem, useRecorder } from '../composables/useRecorder'
import { useSpeech } from '../composables/useSpeech'
import { percent, useModelsStore } from '../stores/models'
import { usePracticeStore } from '../stores/practice'
import type { Topic } from '../types'

const props = defineProps<{ id: number }>()

const store = usePracticeStore()
const speech = useSpeech()
const recorder = useRecorder()

const loading = ref(true)
const error = ref('') // Problems of this page: loading the topic, the microphone.
// The tutor's newest line is heard first; its text is shown only on request.
const showLatest = ref(false)
const bottom = ref<HTMLElement | null>(null)

const busy = computed(() => store.phase !== 'idle')
// Set while the speech recognition model is still downloading, which the first recording waits for.
const models = useModelsStore()
const recognitionDownload = computed(() => {
  const model = models.byId('speech-to-text')
  return model?.state === 'downloading' ? model : null
})
watch(
  () => store.phase,
  (now) => {
    if (now === 'transcribing') void models.check()
  },
)
const latestTutor = computed(() => store.messages.map((m) => m.role).lastIndexOf('tutor'))

function hear(text: string | null) {
  if (!text) return
  showLatest.value = false
  speech.speak(text)
}

function begin(topic: Topic) {
  recorder.release()
  store.begin(topic)
  error.value = ''
  hear(topic.opener)
}

async function startSpeaking() {
  error.value = ''
  store.error = ''
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
    error.value = 'Nothing was recorded. Try again.'
    return
  }
  hear(await store.say(audio))
}

function wrapUp() {
  speech.stop()
  void store.wrapUp()
}

async function retryReply() {
  hear(await store.requestReply())
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const topic = (await api<Topic[]>('/topics')).find((t) => t.id === props.id)
    if (topic) begin(topic)
    else error.value = 'This topic does not exist.'
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

watch(
  () => [store.messages.length, store.review],
  async () => {
    await nextTick()
    bottom.value?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  },
)
watch(() => props.id, load)
onMounted(load)
onBeforeUnmount(() => {
  speech.stop()
  recorder.release()
})
</script>

<template>
  <main class="mx-auto max-w-3xl p-4 sm:p-6">
    <RouterLink class="link text-sm" :to="{ name: 'home' }">‹ All topics</RouterLink>

    <div v-if="loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>

    <template v-else-if="store.topic && store.topic.id === id">
      <header class="mt-2 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 class="text-2xl font-semibold">{{ store.topic.title }}</h1>
          <p class="text-sm text-base-content/70">{{ store.topic.situation }}</p>
        </div>
        <button class="btn btn-ghost btn-sm" :disabled="busy || recorder.recording.value" @click="begin(store.topic)">
          Start over
        </button>
      </header>

      <details v-if="store.topic.background" class="collapse-arrow collapse mt-3 border border-base-300 bg-base-100">
        <summary class="collapse-title text-sm font-medium">What the text was about</summary>
        <p class="collapse-content text-sm text-base-content/80">{{ store.topic.background }}</p>
      </details>

      <section class="mt-4 flex flex-col gap-1" aria-label="Conversation">
        <template v-for="(message, i) in store.messages" :key="i">
          <div class="chat" :class="message.role === 'tutor' ? 'chat-start' : 'chat-end'">
            <div class="chat-header text-xs text-base-content/60">{{ message.role === 'tutor' ? 'Partner' : 'You' }}</div>
            <div class="chat-bubble" :class="message.role === 'learner' ? 'chat-bubble-primary' : ''">
              <template v-if="i === latestTutor && !showLatest">
                <span class="italic opacity-70">{{ speech.speaking.value ? 'Speaking…' : 'Listen first.' }}</span>
              </template>
              <template v-else>{{ message.text }}</template>
            </div>
            <div v-if="i === latestTutor" class="chat-footer mt-1 flex gap-1">
              <button class="btn btn-xs" @click="speech.speak(message.text)">Replay</button>
              <button v-if="!showLatest" class="btn btn-xs" @click="showLatest = true">Show text</button>
            </div>
            <DeliveryNote v-else-if="message.delivery" :delivery="message.delivery" />
          </div>

          <CorrectionCard v-if="message.correction" :correction="message.correction" @hear="speech.speak" />
        </template>

        <div v-if="busy" class="flex items-center gap-2 py-2 text-sm text-base-content/60">
          <MorseSignal animated />
          <template v-if="store.phase === 'transcribing' && recognitionDownload">
            Downloading the speech recognition model (first time only)<template
              v-if="percent(recognitionDownload) !== null"
            >
              — {{ percent(recognitionDownload) }}%</template
            >… What you said is transcribed as soon as it is done.
          </template>
          <template v-else-if="store.phase === 'reviewing'">Writing your summary…</template>
          <template v-else>
            {{ store.phase === 'transcribing' ? 'Listening to what you said…' : 'Your partner is thinking…' }}
          </template>
        </div>

        <template v-if="store.review">
          <ReviewCard class="mt-3" :review="store.review" :messages="store.messages" @hear="speech.speak" />
          <p class="mt-1 text-sm text-base-content/60">
            Saved with this conversation in
            <RouterLink class="link" :to="{ name: 'history' }">History</RouterLink>. Keep talking if you like, and wrap up
            again for a new summary.
          </p>
        </template>
        <div ref="bottom"></div>
      </section>

      <div v-if="error || store.error" role="alert" class="alert alert-error alert-soft mt-4">
        {{ error || store.error }}
      </div>

      <div class="sticky bottom-0 mt-4 flex flex-wrap items-center justify-center gap-2 bg-base-200 py-4">
        <button v-if="recorder.recording.value" class="btn btn-error btn-lg" @click="stopSpeaking">
          <span class="inline-block size-3 animate-pulse rounded-full bg-current"></span>
          Stop
        </button>
        <template v-else>
          <button class="btn btn-primary btn-lg" :disabled="busy" @click="startSpeaking">Start speaking</button>
          <button v-if="store.awaitingReply && !busy" class="btn btn-lg" @click="retryReply">Ask for the reply again</button>
          <button v-if="store.canWrapUp" class="btn btn-lg" :disabled="busy" @click="wrapUp">Wrap up</button>
        </template>
      </div>
    </template>

    <div v-else role="alert" class="alert alert-error mt-4">{{ error || 'This topic could not be opened.' }}</div>
  </main>
</template>
