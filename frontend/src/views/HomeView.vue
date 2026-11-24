<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import MorseSignal from '../components/MorseSignal.vue'
import { isLink, useTopicsStore } from '../stores/topics'

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
        Stuck for words?<br />
        <span class="text-primary">Help is on the way.</span>
      </h1>
      <p class="mt-3 text-base-content/70">
        Pick a topic and talk it through out loud. Your partner answers by voice and fixes your English as you go.
      </p>
    </header>

    <div v-if="store.loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>

    <div v-else class="grid gap-3">
      <div v-if="store.error" role="alert" class="alert alert-error alert-soft">{{ store.error }}</div>

      <div v-if="store.categories.length > 1" class="flex flex-wrap gap-2" role="tablist" aria-label="Topic categories">
        <button
          v-for="category in store.categories"
          :key="category"
          role="tab"
          :aria-selected="category === store.active"
          class="btn btn-sm rounded-full"
          :class="category === store.active ? 'btn-primary' : 'btn-ghost bg-base-100'"
          @click="store.category = category"
        >
          {{ category }}
        </button>
      </div>

      <div v-for="topic in store.shown" :key="topic.id" class="card card-border bg-base-100 transition hover:border-primary">
        <div class="card-body flex-row flex-wrap items-center gap-3">
          <RouterLink class="flex grow basis-64 items-center gap-4" :to="{ name: 'practice', params: { id: topic.id } }">
            <div class="grow">
              <h2 class="card-title text-lg">
                {{ topic.title }}
              </h2>
              <p class="text-sm text-base-content/60">{{ topic.situation }}</p>
            </div>
            <span aria-hidden="true" class="text-2xl text-primary">›</span>
          </RouterLink>
          <template v-if="topic.custom">
            <template v-if="confirming === topic.id">
              <button class="btn btn-error btn-sm" @click="remove(topic.id)">Delete for good</button>
              <button class="btn btn-ghost btn-sm" @click="confirming = null">Keep</button>
            </template>
            <button v-else class="btn btn-ghost btn-sm" :aria-label="`Delete the topic ${topic.title}`" @click="confirming = topic.id">
              Delete
            </button>
          </template>
        </div>
      </div>

      <form v-if="writing" class="card card-border bg-base-100" @submit.prevent="source === 'text' ? addFromText() : add()">
        <div class="card-body gap-3">
          <h2 class="card-title text-lg">A topic of your own</h2>
          <div class="flex flex-wrap gap-2" role="tablist" aria-label="How to make the topic">
            <button
              type="button"
              role="tab"
              :aria-selected="source === 'describe'"
              class="btn btn-sm rounded-full"
              :class="source === 'describe' ? 'btn-neutral' : 'btn-ghost'"
              :disabled="store.adding"
              @click="choose('describe')"
            >
              Describe it
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
              From a link or text
            </button>
          </div>

          <template v-if="source === 'text'">
            <label class="flex flex-col gap-1">
              <span class="text-sm font-medium">Link or text</span>
              <textarea
                v-model="text"
                class="textarea w-full"
                rows="8"
                maxlength="30000"
                required
                placeholder="Paste a link to an article or a speech, or paste the text itself."
              ></textarea>
              <span class="text-xs text-base-content/60">
                Any language works. A link is opened and its text read; pages that need a login and videos cannot be
                read, so paste their text instead. The text is sent to your AI model, which writes a title, a short
                summary to talk from, and your partner's first line. The text itself is not kept.
              </span>
            </label>
          </template>
          <template v-else>
          <label class="flex flex-col gap-1">
            <span class="text-sm font-medium">Title</span>
            <input v-model.trim="draft.title" class="input w-full" maxlength="80" required placeholder="Renting a car" />
          </label>
          <label class="flex flex-col gap-1">
            <span class="text-sm font-medium">Situation</span>
            <textarea
              v-model.trim="draft.situation"
              class="textarea w-full"
              rows="3"
              maxlength="600"
              required
              placeholder="Who your partner is and what you talk about. For example: my partner works at a car rental desk at the airport, and I pick up the car I booked."
            ></textarea>
            <span class="text-xs text-base-content/60">Any language works; the conversation itself is in English.</span>
          </label>
          <label class="flex flex-col gap-1">
            <span class="text-sm font-medium">Your partner's first line <span class="font-normal text-base-content/60">(optional)</span></span>
            <input v-model.trim="draft.opener" class="input w-full" maxlength="400" placeholder="Leave empty to have it written for you" />
          </label>
          </template>
          <div v-if="store.addError" role="alert" class="alert alert-error alert-soft">{{ store.addError }}</div>
          <div class="flex flex-wrap items-center gap-2">
            <button
              class="btn btn-primary btn-sm"
              type="submit"
              :disabled="store.adding || (source === 'text' && !isLink(text) && text.trim().length < MIN_TEXT)"
            >
              {{ source === 'text' ? 'Make the topic' : 'Add the topic' }}
            </button>
            <button class="btn btn-ghost btn-sm" type="button" :disabled="store.adding" @click="writing = false">Cancel</button>
            <span v-if="store.adding" class="flex items-center gap-2 text-sm text-base-content/60">
              <MorseSignal animated /> {{ source === 'text' ? 'Reading it…' : 'Adding…' }}
            </span>
          </div>
        </div>
      </form>
      <button v-else class="btn btn-outline btn-primary justify-self-start" @click="open">+ Add your own topic</button>
    </div>
  </main>
</template>
