<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import MorseSignal from '../components/MorseSignal.vue'
import { isLink, useTopicsStore } from '../stores/topics'
import { useSettingsStore } from '../stores/settings'
import { t, tc } from '../i18n'

const settings = useSettingsStore()

const store = useTopicsStore()

// The form for a topic of the learner's own, shown on request.
const writing = ref(false)
const draft = reactive({ title: '', situation: '', opener: '' })
// How the topic is made: described by the learner, or written from a text they paste in.
const source = ref<'describe' | 'text'>('describe')
const text = ref('')
// Shorter than this there is too little to talk about; the backend refuses it too.
const MIN_TEXT = 100
// The own topic whose "Delete" was pressed once; deleting takes a second press.
const confirming = ref<number | null>(null)

function open() {
  store.addError = ''
  writing.value = true
}

async function add() {
  if (!(await store.add(draft))) return
  Object.assign(draft, { title: '', situation: '', opener: '' })
  writing.value = false
}

async function addFromText() {
  if (!(await store.addFromText(text.value))) return
  text.value = ''
  writing.value = false
}

function choose(next: 'describe' | 'text') {
  store.addError = ''
  source.value = next
}

async function remove(id: number) {
  await store.remove(id)
  confirming.value = null
}

onMounted(() => store.load())
</script>

<template>
  <main class="mx-auto max-w-3xl p-4 sm:p-8">
    <header class="py-8">
      <MorseSignal />
      <h1 class="mt-3 text-4xl font-extrabold tracking-tight sm:text-5xl">
        {{ t('home.headline1') }}<br />
        <span class="text-primary">{{ t('home.headline2') }}</span>
      </h1>
      <p class="mt-3 text-base-content/70">
        {{ t('home.intro', { language: settings.learningName }) }}
      </p>
    </header>

    <div v-if="store.loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>

    <div v-else class="grid gap-3">
      <div v-if="store.error" role="alert" class="alert alert-error alert-soft">{{ store.error }}</div>

      <div v-if="store.categories.length > 1" class="flex flex-wrap gap-2" role="tablist" :aria-label="t('home.categories')">
        <button
          v-for="category in store.categories"
          :key="category"
          role="tab"
          :aria-selected="category === store.active"
          class="btn btn-sm rounded-full"
          :class="category === store.active ? 'btn-primary' : 'btn-ghost bg-base-100'"
          @click="store.category = category"
        >
          {{ tc(category) }}
        </button>
      </div>

      <div v-for="topic in store.shown" :key="topic.id" class="card card-border bg-base-100 transition hover:border-primary">
        <div class="card-body flex-row flex-wrap items-center gap-3">
          <RouterLink class="flex grow basis-64 items-center gap-4" :to="{ name: 'practice', params: { id: topic.id } }">
            <div class="grow">
              <h2 class="card-title text-lg">
                {{ tc(topic.title) }}
              </h2>
              <p class="text-sm text-base-content/60">{{ tc(topic.situation) }}</p>
            </div>
            <span aria-hidden="true" class="text-2xl text-primary">›</span>
          </RouterLink>
          <template v-if="topic.custom">
            <template v-if="confirming === topic.id">
              <button class="btn btn-error btn-sm" @click="remove(topic.id)">{{ t('common.deleteForGood') }}</button>
              <button class="btn btn-ghost btn-sm" @click="confirming = null">{{ t('common.keep') }}</button>
            </template>
            <button v-else class="btn btn-ghost btn-sm" :aria-label="t('home.deleteTopic', { title: topic.title })" @click="confirming = topic.id">
              {{ t('common.delete') }}
            </button>
          </template>
        </div>
      </div>

      <form v-if="writing" class="card card-border bg-base-100" @submit.prevent="source === 'text' ? addFromText() : add()">
        <div class="card-body gap-3">
          <h2 class="card-title text-lg">{{ t('home.ownTitle') }}</h2>
          <div class="flex flex-wrap gap-2" role="tablist" :aria-label="t('home.how')">
            <button
              type="button"
              role="tab"
              :aria-selected="source === 'describe'"
              class="btn btn-sm rounded-full"
              :class="source === 'describe' ? 'btn-neutral' : 'btn-ghost'"
              :disabled="store.adding"
              @click="choose('describe')"
            >
              {{ t('home.describe') }}
            </button>
            <button
              type="button"
              role="tab"
              :aria-selected="source === 'text'"
              class="btn btn-sm rounded-full"
              :class="source === 'text' ? 'btn-neutral' : 'btn-ghost'"
              :disabled="store.adding"
              @click="choose('text')"
            >
              {{ t('home.fromText') }}
            </button>
          </div>

          <template v-if="source === 'text'">
            <label class="flex flex-col gap-1">
              <span class="text-sm font-medium">{{ t('home.linkOrText') }}</span>
              <textarea
                v-model="text"
                class="textarea w-full"
                rows="8"
                maxlength="30000"
                required
                :placeholder="t('home.textPlaceholder')"
              ></textarea>
              <span class="text-xs text-base-content/60">
                {{ t('home.textHelp') }}
              </span>
            </label>
          </template>
          <template v-else>
          <label class="flex flex-col gap-1">
            <span class="text-sm font-medium">{{ t('home.title') }}</span>
            <input v-model.trim="draft.title" class="input w-full" maxlength="80" required :placeholder="t('home.titlePlaceholder')" />
          </label>
          <label class="flex flex-col gap-1">
            <span class="text-sm font-medium">{{ t('home.situation') }}</span>
            <textarea
              v-model.trim="draft.situation"
              class="textarea w-full"
              rows="3"
              maxlength="600"
              required
              :placeholder="t('home.situationPlaceholder')"
            ></textarea>
            <span class="text-xs text-base-content/60">{{ t('home.situationHelp', { language: settings.learningName }) }}</span>
          </label>
          <label class="flex flex-col gap-1">
            <span class="text-sm font-medium">{{ t('home.opener') }} <span class="font-normal text-base-content/60">{{ t('home.optional') }}</span></span>
            <input v-model.trim="draft.opener" class="input w-full" maxlength="400" :placeholder="t('home.openerPlaceholder')" />
          </label>
          </template>
          <div v-if="store.addError" role="alert" class="alert alert-error alert-soft">{{ store.addError }}</div>
          <div class="flex flex-wrap items-center gap-2">
            <button
              class="btn btn-primary btn-sm"
              type="submit"
              :disabled="store.adding || (source === 'text' && !isLink(text) && text.trim().length < MIN_TEXT)"
            >
              {{ source === 'text' ? t('home.make') : t('home.add') }}
            </button>
            <button class="btn btn-ghost btn-sm" type="button" :disabled="store.adding" @click="writing = false">{{ t('common.cancel') }}</button>
            <span v-if="store.adding" class="flex items-center gap-2 text-sm text-base-content/60">
              <MorseSignal animated /> {{ source === 'text' ? t('home.reading') : t('common.adding') }}
            </span>
          </div>
        </div>
      </form>
      <button v-else class="btn btn-outline btn-primary justify-self-start" @click="open">{{ t('home.addOwn') }}</button>
    </div>
  </main>
</template>
