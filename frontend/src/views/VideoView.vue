<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import MorseSignal from '../components/MorseSignal.vue'
import { micProblem, useRecorder } from '../composables/useRecorder'
import { useYouTubePlayer } from '../composables/useYouTubePlayer'
import { usePatternsStore } from '../stores/patterns'
import { useShadowStore } from '../stores/shadow'
import { LEVELS, useVideosStore } from '../stores/videos'
import type { PatternStatus, Video } from '../types'
import { clock, lineAt, pick, stepFrom } from '../video'
import { useSettingsStore } from '../stores/settings'
import { t, tc } from '../i18n'

const settings = useSettingsStore()

// A saved video, listened to one sentence at a time, and shadowed: said after the speaker.
const props = defineProps<{ id: number }>()

// A sentence's start is worked out from its subtitle line, so playing starts a moment early.
const LEAD = 0.25
const RATES = [0.5, 0.75, 1]

const video = ref<Video | null>(null)
const loading = ref(true)
const error = ref('')
const frame = ref<HTMLElement | null>(null)
const list = ref<HTMLElement | null>(null)
const player = useYouTubePlayer(frame)
const route = useRoute()
const recorder = useRecorder()
const shadow = useShadowStore()
// Problems of this page: the microphone.
const micError = ref('')

// The video's level: set by hand, or estimated again from its subtitles.
const videos = useVideosStore()
const estimating = ref(false)

async function setLevel(level: string) {
  if (!video.value) return
  const changed = await videos.setLevel(video.value.id, level || null)
  if (changed) video.value.level = changed.level
}

// Videos like this one, at a similar level, to study with next.
const router = useRouter()
const suggested = computed(() => video.value !== null && videos.suggestedFor === video.value.id)
// The suggested video being added.
const adding = ref('')

async function addSuggested(videoId: string) {
  adding.value = videoId
  const added = await videos.add(`https://youtu.be/${videoId}`)
  adding.value = ''
  if (added) await router.push({ name: 'video', params: { id: added.id } })
}

async function estimateLevel() {
  if (!video.value) return
  estimating.value = true
  const changed = await videos.estimateLevel(video.value.id)
  if (changed) video.value.level = changed.level
  estimating.value = false
}

// Making a pattern from the chosen sentence: the sentence it is made from, its words, the
// stretch of them the learner marked, and the pattern once it is made.
const patterns = usePatternsStore()
const marking = ref<number | null>(null)
const marked = ref<[number, number] | null>(null)
const made = ref<PatternStatus | null>(null)

// The sentence chosen by the learner; while the video plays on, the one being said.
const chosen = ref(-1)
const repeat = ref(false)
const rate = ref(1)
const showText = ref(true)

const lines = computed(() => video.value?.lines ?? [])
// The chosen sentence while it plays on its own or before anything was played; otherwise the
// one being said.
const current = computed(() =>
  player.part.value || (chosen.value >= 0 && !player.playing.value) ? chosen.value : lineAt(lines.value, player.time.value),
)
// While the video plays on by itself, the sentence being said becomes the chosen one, so
// that pausing leaves the learner on it.
watch(
  () => (!player.part.value && player.playing.value ? lineAt(lines.value, player.time.value) : -1),
  (said) => {
    if (said >= 0) chosen.value = said
  },
)
const result = computed(() => (shadow.result?.line === lines.value[current.value]?.id ? shadow.result : null))

function play(index: number) {
  const line = lines.value[index]
  if (!line) return
  if (index !== chosen.value) {
    shadow.clear()
    stopMarking()
  }
  chosen.value = index
  player.playPart(Math.max(0, line.start - LEAD), line.end, repeat.value)
}

function step(by: 1 | -1) {
  play(stepFrom(lines.value, current.value, by))
}

function toggle() {
  if (player.playing.value) player.pause()
  else play(current.value < 0 ? 0 : current.value)
}

const markWords = computed(() => (marking.value === null ? [] : (lines.value[marking.value]?.text.split(' ') ?? [])))
const phrase = computed(() => (marked.value ? markWords.value.slice(marked.value[0], marked.value[1] + 1).join(' ') : ''))

function startMarking() {
  if (current.value < 0) return
  chosen.value = current.value
  player.pause()
  patterns.makeError = ''
  made.value = null
  marked.value = null
  marking.value = current.value
}

function stopMarking() {
  marking.value = null
  marked.value = null
  made.value = null
}

async function makePattern() {
  const line = marking.value === null ? null : lines.value[marking.value]
  if (line && phrase.value) made.value = await patterns.make(line.id, phrase.value)
}

// Shadowing is listen, then say: the video is stopped while the learner speaks, or its sound
// would be recorded too.
async function startShadowing() {
  if (current.value < 0) return
  chosen.value = current.value
  player.pause()
  micError.value = ''
  shadow.clear()
  try {
    await recorder.start()
  } catch (e) {
    micError.value = micProblem(e)
  }
}

async function stopShadowing() {
  const audio = await recorder.stop()
  const line = lines.value[chosen.value]
  if (!audio) micError.value = t('common.nothingRecorded')
  else if (line) await shadow.attempt(line, audio)
}

async function load() {
  loading.value = true
  error.value = ''
  video.value = null
  videos.error = ''
  chosen.value = -1
  shadow.clear()
  stopMarking()
  recorder.release()
  try {
    video.value = await api<Video>(`/videos/${props.id}`)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
  if (!video.value) return
  // A sentence found by the search is opened ready to be played.
  const wanted = Number(route.query.line)
  if (Number.isInteger(wanted) && lines.value[wanted]) chosen.value = wanted
  await nextTick()
  await player.open(video.value.video_id)
}

// The translation is asked for when it is turned on, and for each video opened while it is on.
function translateIfShown() {
  const id = video.value?.id
  if (id === undefined || !videos.showTranslation) return
  if (videos.translatedFor === id && (videos.translating || Object.keys(videos.translations).length)) return
  videos.translate(id)
}
watch(() => [videos.showTranslation, video.value?.id], translateIfShown)

watch(rate, (now) => player.setRate(now))
watch(player.ready, (now) => now && player.setRate(rate.value))
// With the text hidden, the subtitles on the video itself are hidden as well.
watch(showText, (now) => player.setCaptions(now))
// The subtitles come back when a video starts to play, so they are hidden again then.
watch(player.playing, (now) => now && !showText.value && player.setCaptions(false))
// Repeating starts or stops for the sentence that is playing, too.
watch(repeat, (now) => {
  if (player.part.value) player.part.value.repeat = now
})
watch(current, async (now) => {
  await nextTick()
  list.value?.querySelector(`[data-line="${now}"]`)?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' })
})
watch(() => props.id, load)
onMounted(load)
onBeforeUnmount(() => recorder.release())
</script>

<template>
  <main class="mx-auto max-w-3xl p-4 sm:p-6">
    <RouterLink class="link text-sm" :to="{ name: 'videos' }">{{ t('video.all') }}</RouterLink>

    <div v-if="loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>

    <template v-else-if="video">
      <header class="mt-2">
        <h1 class="text-2xl font-semibold">{{ video.title }}</h1>
        <p class="text-sm text-base-content/70">
          <template v-if="video.channel">{{ video.channel }} · </template>{{ t('common.sentences', { n: lines.length })
          }}<template v-if="video.generated">{{ t('video.automaticNote') }}</template>
        </p>
        <div class="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <label class="flex items-center gap-2">
            {{ t('video.level') }}
            <select
              class="select select-sm w-28"
              :value="video.level ?? ''"
              :aria-label="t('video.levelOf')"
              @change="setLevel(($event.target as HTMLSelectElement).value)"
            >
              <option value="">{{ t('video.none') }}</option>
              <option v-for="level in LEVELS" :key="level" :value="level">{{ level }}</option>
            </select>
          </label>
          <button class="btn btn-ghost btn-sm" :disabled="estimating" @click="estimateLevel">{{ t('video.estimate') }}</button>
          <span v-if="estimating" class="flex items-center gap-2 text-base-content/60"><MorseSignal animated /> {{ t('video.estimating') }}</span>
          <span v-if="videos.error" role="alert" class="text-error">{{ videos.error }}</span>
          <button class="btn btn-ghost btn-sm" :disabled="videos.suggesting" @click="videos.suggest(video.id)">
            {{ t('video.similar') }}
          </button>
        </div>

        <section v-if="suggested" class="mt-2 rounded-box bg-base-100 p-3 text-sm" :aria-label="t('video.similarList')">
          <p v-if="videos.suggesting" class="flex items-center gap-2 text-base-content/60">
            <MorseSignal animated /> {{ t('video.looking') }}
          </p>
          <div v-else-if="videos.suggestError" role="alert" class="alert alert-error alert-soft">{{ videos.suggestError }}</div>
          <p v-else-if="!videos.suggestions.length" class="text-base-content/60">
            {{ t('video.noSimilar', { language: settings.learningName }) }}
          </p>
          <ul v-else class="grid gap-2">
            <li v-for="s in videos.suggestions" :key="s.video_id" class="flex flex-wrap items-center gap-x-3 gap-y-1">
              <div class="min-w-0 flex-1">
                <p class="font-medium">{{ s.title }}</p>
                <p class="text-base-content/60">
                  <template v-if="s.channel">{{ s.channel }} · </template>
                  <template v-if="s.duration !== null">{{ clock(s.duration) }} · </template>
                  <span class="badge badge-soft badge-primary badge-sm">{{ s.level }}</span>
                  <template v-if="s.generated">{{ t('video.automatic') }}</template>
                </p>
              </div>
              <button class="btn btn-primary btn-sm" :disabled="videos.adding" @click="addSuggested(s.video_id)">
                {{ adding === s.video_id ? t('common.adding') : t('video.add') }}
              </button>
            </li>
          </ul>
          <div v-if="videos.addError" role="alert" class="alert alert-error alert-soft mt-2">{{ videos.addError }}</div>
        </section>
      </header>

      <div class="sticky top-0 z-10 -mx-4 mt-3 bg-base-200 px-4 pb-3 sm:-mx-6 sm:px-6">
        <div ref="frame" class="video-frame aspect-video w-full overflow-hidden rounded-box bg-neutral"></div>
        <div v-if="player.error.value" role="alert" class="alert alert-error alert-soft mt-2">{{ player.error.value }}</div>

        <div class="mt-3 flex flex-wrap items-center gap-2">
          <button class="btn btn-sm" :disabled="!player.ready.value" :aria-label="t('video.previousSentence')" @click="step(-1)">{{ t('video.previous') }}</button>
          <button class="btn btn-primary btn-sm" :disabled="!player.ready.value" @click="toggle">
            {{ player.playing.value ? t('video.pause') : t('video.play') }}
          </button>
          <button class="btn btn-sm" :disabled="!player.ready.value" :aria-label="t('video.nextSentence')" @click="step(1)">{{ t('video.next') }}</button>
          <label class="label cursor-pointer gap-2 text-sm">
            <input v-model="repeat" type="checkbox" class="toggle toggle-sm" />
            {{ t('video.repeat') }}
          </label>
          <label class="flex items-center gap-2 text-sm">
            {{ t('video.speed') }}
            <select v-model.number="rate" class="select select-sm w-24">
              <option v-for="r in RATES" :key="r" :value="r">{{ r }}×</option>
            </select>
          </label>
          <label class="label cursor-pointer gap-2 text-sm">
            <input v-model="showText" type="checkbox" class="toggle toggle-sm" />
            {{ t('video.showText') }}
          </label>
          <label class="label cursor-pointer gap-2 text-sm" :title="t('video.translationHint')">
            <input v-model="videos.showTranslation" type="checkbox" class="toggle toggle-sm" />
            {{ t('video.translation') }}
          </label>
          <button v-if="recorder.recording.value" class="btn btn-error btn-sm" @click="stopShadowing">
            <span class="inline-block size-2 animate-pulse rounded-full bg-current"></span>
            {{ t('common.stop') }}
          </button>
          <button
            v-else
            class="btn btn-sm btn-neutral"
            :disabled="!player.ready.value || current < 0 || shadow.checking"
            :title="t('video.sayAfterHint')"
            @click="startShadowing"
          >
            {{ t('video.sayAfter') }}
          </button>
          <button
            class="btn btn-sm"
            :disabled="!player.ready.value || current < 0 || marking !== null"
            :title="t('video.makePatternHint')"
            @click="startMarking"
          >
            {{ t('video.makePattern') }}
          </button>
        </div>

        <p v-if="videos.showTranslation && videos.translating" class="mt-2 flex items-center gap-2 text-sm text-base-content/60">
          <MorseSignal animated /> {{ t('video.translating') }}
        </p>
        <div v-else-if="videos.showTranslation && videos.translateError" role="alert" class="alert alert-error alert-soft mt-2">
          {{ videos.translateError }}
          <button class="btn btn-sm" @click="video && videos.translate(video.id)">{{ t('common.tryAgain') }}</button>
        </div>
        <div
          v-else-if="videos.showTranslation && videos.translatedFor === video.id && videos.untranslated"
          role="status"
          class="alert alert-warning alert-soft mt-2"
        >
          {{ t('video.untranslated', { n: videos.untranslated }) }}
          <button class="btn btn-sm" @click="videos.translate(video.id)">{{ t('common.tryAgain') }}</button>
        </div>

        <div v-if="marking !== null" class="mt-2 rounded-box bg-base-100 p-3 text-sm">
          <template v-if="made">
            <p class="text-base-content/60">{{ t('video.savedPattern') }}</p>
            <p class="text-base font-medium">{{ made.pattern }}</p>
            <p class="text-base-content/70">{{ tc(made.use) }}</p>
            <div class="mt-2 flex flex-wrap gap-2">
              <RouterLink class="btn btn-primary btn-sm" :to="{ name: 'pattern', params: { id: made.id } }">{{ t('video.practiseIt') }}</RouterLink>
              <button class="btn btn-ghost btn-sm" @click="stopMarking">{{ t('common.close') }}</button>
            </div>
          </template>
          <template v-else>
            <p class="text-base-content/60">{{ t('video.markHelp') }}</p>
            <p class="mt-1 flex flex-wrap gap-1 text-base">
              <button
                v-for="(word, i) in markWords"
                :key="i"
                class="rounded px-1 transition hover:bg-primary/15"
                :class="marked && i >= marked[0] && i <= marked[1] ? 'bg-primary text-primary-content hover:bg-primary' : ''"
                :aria-pressed="!!marked && i >= marked[0] && i <= marked[1]"
                :disabled="patterns.making"
                @click="marked = pick(marked, i)"
              >
                {{ word }}
              </button>
            </p>
            <div class="mt-2 flex flex-wrap items-center gap-2">
              <button class="btn btn-primary btn-sm" :disabled="!phrase || patterns.making" @click="makePattern">{{ t('video.makeThePattern') }}</button>
              <button class="btn btn-ghost btn-sm" :disabled="patterns.making" @click="stopMarking">{{ t('common.cancel') }}</button>
              <span v-if="patterns.making" class="flex items-center gap-2 text-base-content/60">
                <MorseSignal animated /> {{ t('video.working') }}
              </span>
            </div>
            <div v-if="patterns.makeError" role="alert" class="alert alert-error alert-soft mt-2">{{ patterns.makeError }}</div>
          </template>
        </div>

        <div v-if="shadow.checking" class="mt-2 flex items-center gap-2 text-sm text-base-content/60">
          <MorseSignal animated /> {{ t('common.listening') }}
        </div>
        <div v-else-if="result" class="mt-2 rounded-box bg-base-100 p-3 text-sm" aria-live="polite">
          <p class="font-medium" :class="result.accuracy === 100 ? 'text-success' : 'text-primary'">
            {{ result.accuracy === 100 ? t('video.allHeard') : t('video.someHeard', { n: result.accuracy }) }}
          </p>
          <p class="mt-1 text-base">
            <template v-for="(word, i) in result.words" :key="i">
              <span :class="word.heard ? '' : 'rounded bg-primary/15 px-0.5 font-semibold text-primary'">{{ word.text }}</span
              >{{ ' ' }}
            </template>
          </p>
          <p class="mt-1 text-base-content/60">{{ t('common.youSaid') }} {{ result.heard }}</p>
        </div>
        <div v-if="micError || shadow.error" role="alert" class="alert alert-error alert-soft mt-2">
          {{ micError || shadow.error }}
        </div>
      </div>

      <ol ref="list" class="mt-2 grid gap-1" :aria-label="t('video.sentences')">
        <li v-for="(line, i) in lines" :key="i" :data-line="i">
          <button
            class="flex w-full items-baseline gap-3 rounded-lg px-3 py-2 text-left transition hover:bg-base-100"
            :class="i === current ? 'bg-base-100 ring-2 ring-primary' : ''"
            :aria-current="i === current"
            :disabled="!player.ready.value"
            @click="play(i)"
          >
            <span class="w-12 shrink-0 text-xs text-base-content/50 tabular-nums">{{ clock(line.start) }}</span>
            <span class="flex flex-col">
              <span v-if="showText">{{ line.text }}</span>
              <span v-else class="italic text-base-content/40">{{ t('video.sentenceN', { n: i + 1 }) }}</span>
              <span
                v-if="videos.showTranslation && videos.translatedFor === video.id && videos.translations[line.id]"
                class="text-sm text-base-content/60"
                >{{ videos.translations[line.id] }}</span
              >
            </span>
            <span
              v-if="line.best !== null"
              class="badge badge-soft badge-sm ml-auto shrink-0"
              :class="line.best === 100 ? 'badge-success' : 'badge-neutral'"
              :title="t('video.shadowed', { n: line.shadowed, best: line.best })"
            >
              {{ line.best }}%
            </span>
          </button>
        </li>
      </ol>
    </template>

    <div v-else role="alert" class="alert alert-error mt-4">{{ error || t('video.cannotOpen') }}</div>
  </main>
</template>

<style scoped>
/* YouTube's player comes as an iframe with a fixed size; it fills the frame instead. */
.video-frame :deep(iframe) {
  width: 100%;
  height: 100%;
}
</style>
