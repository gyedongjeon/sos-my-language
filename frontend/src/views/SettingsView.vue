<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { useSpeech } from '../composables/useSpeech'
import { megabytes, useModelsStore } from '../stores/models'
import { LANGUAGES, useSettingsStore } from '../stores/settings'
import type { LLMSettings } from '../types'
import { languageName, t, voiceLabel } from '../i18n'

// `prefix` is the provider name LiteLLM expects in front of the model.
const PROVIDERS = [
  {
    id: 'gemini',
    label: 'Google Gemini',
    prefix: 'gemini/',
    model: 'gemini-3.1-flash-lite',
    example: 'gemini-3.1-flash-lite',
    keyUrl: 'https://aistudio.google.com/apikey',
  },
  {
    id: 'anthropic',
    label: 'Anthropic Claude',
    prefix: 'anthropic/',
    model: 'claude-haiku-5-5',
    example: 'claude-haiku-5-5',
    keyUrl: 'https://console.anthropic.com/settings/keys',
  },
  {
    id: 'openai',
    label: 'OpenAI',
    prefix: 'openai/',
    model: '',
    example: 'gpt-4o-mini',
    keyUrl: 'https://platform.openai.com/api-keys',
  },
  {
    id: 'openrouter',
    label: 'OpenRouter',
    prefix: 'openrouter/',
    model: '',
    example: 'google/gemini-2.5-flash-lite',
    keyUrl: 'https://openrouter.ai/keys',
  },
  // Anything else LiteLLM supports, written out in full as "<provider>/<model>".
  { id: 'other', label: 'Other (LiteLLM)', prefix: '', model: '', example: 'mistral/mistral-small-latest', keyUrl: '' },
] as const

// Third-party work shipped in the built app; the full texts are in public/THIRD_PARTY_NOTICES.txt.
const CREDITS = [
  { name: 'Bricolage Grotesque (heading font)', copyright: '© 2022 The Bricolage Grotesque Project Authors', license: 'SIL OFL 1.1' },
  { name: 'Vue', copyright: '© 2018-present Yuxi (Evan) You', license: 'MIT' },
  { name: 'Vue Router', copyright: '© 2019-present Eduardo San Martin Morote', license: 'MIT' },
  { name: 'Pinia', copyright: '© 2019-present Eduardo San Martin Morote', license: 'MIT' },
  { name: 'daisyUI', copyright: '© 2020 Pouya Saadeghi', license: 'MIT' },
  { name: 'Tailwind CSS', copyright: '© Tailwind Labs, Inc.', license: 'MIT' },
  { name: 'uv (desktop app)', copyright: '© 2025 Astral Software Inc.', license: 'MIT' },
]

const store = useSettingsStore()
const providerId = ref<(typeof PROVIDERS)[number]['id']>('gemini')
const model = ref<string>(PROVIDERS[0].model)
const apiKey = ref('')
const busy = ref(false)
const error = ref('')
const success = ref('')

const provider = computed(() => PROVIDERS.find((p) => p.id === providerId.value)!)
const saved = computed(() => store.llm)
// The saved key can be kept only while the provider stays the one it was saved for.
const canKeepKey = computed(
  () =>
    Boolean(saved.value?.key_hint) &&
    (saved.value!.model ?? '').split('/')[0] === (provider.value.prefix + model.value).split('/')[0],
)

function show(settings: LLMSettings) {
  if (!settings.model) return
  const match = PROVIDERS.find((p) => p.prefix && settings.model!.startsWith(p.prefix))
  providerId.value = match?.id ?? 'other'
  model.value = match ? settings.model.slice(match.prefix.length) : settings.model
}

function onProviderChange() {
  model.value = provider.value.model
  apiKey.value = ''
}

async function save() {
  error.value = ''
  success.value = ''
  busy.value = true
  try {
    store.llm = await api<LLMSettings>('/settings/llm', {
      method: 'PUT',
      json: { model: provider.value.prefix + model.value.trim(), api_key: apiKey.value.trim() },
    })
    apiKey.value = ''
  } catch (e) {
    error.value = t('settings.saveFailed', { error: (e as Error).message })
    busy.value = false
    return
  }
  try {
    await api('/settings/llm/test', { method: 'POST' })
    success.value = t('settings.saved')
  } catch (e) {
    error.value = t('settings.testFailed', { error: (e as Error).message })
  } finally {
    busy.value = false
  }
}

async function remove() {
  error.value = ''
  success.value = ''
  busy.value = true
  try {
    store.llm = await api<LLMSettings>('/settings/llm', { method: 'DELETE' })
    apiKey.value = ''
  } catch (e) {
    error.value = t('settings.removeFailed', { error: (e as Error).message })
  } finally {
    busy.value = false
  }
}

// The partner's voice: chosen from a few of the language being practised, heard before or after
// choosing it.
const speech = useSpeech()
const models = useModelsStore()
const chosenVoice = computed(() => store.voices.find((v) => v.chosen) ?? null)

// Once a download ends, the list says which voices are there.
watch(
  () => models.active.length,
  (now, before) => {
    if (before && !now) void store.loadVoices()
  },
)

async function chooseVoice(voice: string) {
  speech.stop()
  // The download it starts is shown under the navigation bar.
  if (await store.setVoice(voice)) await models.check()
}

// Another language to practise: its own voices are listed, and its speech models downloaded.
async function chooseLanguage(code: string) {
  speech.stop()
  await store.chooseLanguage(code)
}

onMounted(async () => {
  void store.loadVoices()
  await store.loadLLM()
  if (store.llm) show(store.llm)
})
</script>

<template>
  <main class="mx-auto max-w-3xl p-4 sm:p-6">
    <h1 class="text-2xl font-semibold">{{ saved && !saved.model ? t('settings.welcome') : t('nav.settings') }}</h1>
    <p v-if="saved && !saved.model" class="mt-1 text-base-content/70">
      {{ t('settings.welcomeBody') }}
      <RouterLink class="link" to="/">{{ t('settings.skip') }}</RouterLink>
    </p>

    <section class="card mt-4 bg-base-100 shadow-sm">
      <div class="card-body gap-4">
        <div>
          <h2 class="card-title">{{ t('nav.practise') }}</h2>
          <p class="text-sm text-base-content/70">
            {{ t('settings.practiseBody') }}
          </p>
        </div>
        <label class="flex flex-col gap-1">
          <span class="text-sm font-medium">{{ t('common.language') }}</span>
          <select
            class="select w-full"
            :value="store.learning?.code ?? ''"
            @change="chooseLanguage(($event.target as HTMLSelectElement).value)"
          >
            <option v-for="l in store.languages ?? []" :key="l.code" :value="l.code">
              {{ l.native === languageName(l.code, l.name) ? l.native : `${l.native} (${languageName(l.code, l.name)})` }}
            </option>
          </select>
          <span class="text-xs text-base-content/60">
            {{ t('settings.practiseNote') }}
          </span>
        </label>
      </div>
    </section>

    <section class="card mt-4 bg-base-100 shadow-sm">
      <div class="card-body gap-4">
        <div>
          <h2 class="card-title">{{ t('settings.yourLanguage') }}</h2>
          <p class="text-sm text-base-content/70">
            {{ t('settings.yourLanguageBody', { language: store.learningName }) }}
          </p>
        </div>
        <label class="flex flex-col gap-1">
          <span class="text-sm font-medium">{{ t('common.language') }}</span>
          <select
            class="select w-full"
            :value="store.feedbackLanguage"
            @change="store.setFeedbackLanguage(($event.target as HTMLSelectElement).value)"
          >
            <option v-for="l in LANGUAGES" :key="l.name" :value="l.name">{{ l.label }}</option>
          </select>
          <span class="text-xs text-base-content/60">
            {{ t('settings.yourLanguageNote') }}
          </span>
        </label>
      </div>
    </section>

    <section class="card mt-4 bg-base-100 shadow-sm">
      <div class="card-body gap-4">
        <div>
          <h2 class="card-title">{{ t('models.voice') }}</h2>
          <p class="text-sm text-base-content/70">
            {{ t('settings.voiceBody', { language: store.learningName }) }}
          </p>
        </div>
        <div class="flex flex-wrap items-end gap-2">
          <label class="flex min-w-64 flex-1 flex-col gap-1">
            <span class="text-sm font-medium">{{ t('settings.voice') }}</span>
            <select
              class="select w-full"
              :value="store.voice ?? ''"
              :disabled="!store.voices.length"
              @change="chooseVoice(($event.target as HTMLSelectElement).value)"
            >
              <option v-for="v in store.voices" :key="v.id" :value="v.id">
                {{ voiceLabel(v.label) }}{{ v.downloaded ? '' : t('settings.toDownload', { n: megabytes(v.size) }) }}
              </option>
            </select>
          </label>
          <button
            class="btn"
            :disabled="!chosenVoice || !store.learning"
            @click="speech.speaking.value ? speech.stop() : speech.speak(store.learning?.sample ?? '')"
          >
            {{ speech.speaking.value ? t('common.stop') : t('common.hearIt') }}
          </button>
        </div>
        <span v-if="chosenVoice && !chosenVoice.downloaded" class="text-xs text-base-content/60">
          {{ t('settings.voiceFallback') }}
        </span>
      </div>
    </section>

    <section class="card mt-4 bg-base-100 shadow-sm">
      <form class="card-body gap-4" @submit.prevent="save">
        <div>
          <h2 class="card-title">{{ t('settings.ai') }}</h2>
          <p class="text-sm text-base-content/70">
            {{ t('settings.aiBody') }}
          </p>
        </div>

        <p v-if="saved?.source === 'app'" class="text-sm">
          {{ t('settings.current') }} <span class="font-mono">{{ saved.model }}</span>
          <span v-if="saved.key_hint" class="text-base-content/60">{{ t('settings.keyEnding', { hint: saved.key_hint }) }}</span>
        </p>
        <p v-else-if="saved?.source === 'env'" class="text-sm">
          {{ t('settings.current') }} <span class="font-mono">{{ saved.model }}</span>
          <span class="text-base-content/60">{{ t('settings.fromEnv') }}</span>
        </p>
        <p v-else class="text-sm text-warning">{{ t('settings.noModel') }}</p>

        <label class="flex flex-col gap-1">
          <span class="text-sm font-medium">{{ t('settings.provider') }}</span>
          <select v-model="providerId" class="select w-full" :disabled="busy" @change="onProviderChange">
            <option v-for="p in PROVIDERS" :key="p.id" :value="p.id">{{ p.label }}</option>
          </select>
        </label>

        <label class="flex flex-col gap-1">
          <span class="text-sm font-medium">{{ t('settings.model') }}</span>
          <input
            v-model="model"
            class="input w-full font-mono"
            :placeholder="t('settings.example', { example: provider.example })"
            :disabled="busy"
            required
            spellcheck="false"
          />
          <span v-if="providerId === 'other'" class="text-xs text-base-content/60">
            {{ t('settings.otherHelp') }}
          </span>
          <span v-else class="text-xs text-base-content/60">{{ t('settings.modelHelp') }}</span>
        </label>

        <label class="flex flex-col gap-1">
          <span class="text-sm font-medium">{{ t('settings.apiKey') }}</span>
          <input
            v-model="apiKey"
            type="password"
            class="input w-full font-mono"
            :placeholder="canKeepKey ? t('settings.keepKey') : t('settings.pasteKey')"
            :required="!canKeepKey"
            :disabled="busy"
            autocomplete="off"
            spellcheck="false"
          />
          <a v-if="provider.keyUrl" class="link text-xs" :href="provider.keyUrl" target="_blank" rel="noreferrer">
            {{ t('settings.getKey', { provider: provider.label }) }}
          </a>
        </label>

        <div v-if="error" role="alert" class="alert alert-error alert-soft">{{ error }}</div>
        <div v-if="success" role="status" class="alert alert-success alert-soft">{{ success }}</div>

        <div class="card-actions items-center">
          <button class="btn btn-primary" :disabled="busy">
            <span v-if="busy" class="loading loading-spinner loading-sm"></span>
            {{ t('settings.saveTest') }}
          </button>
          <button v-if="saved?.source === 'app'" type="button" class="btn btn-ghost" :disabled="busy" @click="remove">
            {{ t('settings.remove') }}
          </button>
        </div>
      </form>
    </section>

    <section class="card mt-4 bg-base-100 shadow-sm">
      <div class="card-body gap-4">
        <div>
          <h2 class="card-title">{{ t('settings.openSource') }}</h2>
          <p class="text-sm text-base-content/70">
            {{ t('settings.openSourceBody') }}
          </p>
        </div>
        <ul class="list">
          <li v-for="c in CREDITS" :key="c.name" class="list-row items-center px-0">
            <div class="list-col-grow">
              <p class="font-medium">{{ c.name }}</p>
              <p class="text-xs text-base-content/60">{{ c.copyright }}</p>
            </div>
            <span class="badge badge-soft badge-sm">{{ c.license }}</span>
          </li>
        </ul>
        <a class="link text-sm" href="/THIRD_PARTY_NOTICES.txt" target="_blank" rel="noreferrer">
          {{ t('settings.licenses') }}
        </a>
      </div>
    </section>
  </main>
</template>
