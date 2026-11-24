<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import CorrectionCard from '../components/CorrectionCard.vue'
import DeliveryNote from '../components/DeliveryNote.vue'
import MorseSignal from '../components/MorseSignal.vue'
import ReviewCard from '../components/ReviewCard.vue'
import { useSpeech } from '../composables/useSpeech'
import { fromSaved, startedOn } from '../history'
import type { Review, SavedConversation } from '../types'

// A saved conversation, to read and listen to again.
const props = defineProps<{ id: number }>()

const speech = useSpeech()
const conversation = ref<SavedConversation | null>(null)
const loading = ref(true)
const error = ref('')
const messages = computed(() => (conversation.value?.messages ?? []).map(fromSaved))
// A conversation that was not wrapped up at the time can be summarized here.
const reviewing = ref(false)
const reviewError = ref('')

async function summarize() {
  const reviewed = conversation.value
  if (!reviewed) return
  reviewing.value = true
  reviewError.value = ''
  try {
    reviewed.review = await api<Review>(`/conversations/${reviewed.id}/review`, { method: 'POST' })
  } catch (e) {
    reviewError.value = `Could not write the summary: ${(e as Error).message}`
  } finally {
    reviewing.value = false
  }
}

async function load() {
  loading.value = true
  error.value = ''
  reviewError.value = ''
  conversation.value = null
  try {
    conversation.value = await api<SavedConversation>(`/conversations/${props.id}`)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

watch(() => props.id, load)
onMounted(load)
onBeforeUnmount(() => speech.stop())
</script>

<template>
  <main class="mx-auto max-w-3xl p-4 sm:p-6">
    <RouterLink class="link text-sm" :to="{ name: 'history' }">‹ History</RouterLink>

    <div v-if="loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>

    <template v-else-if="conversation">
      <header class="mt-2 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 class="text-2xl font-semibold">{{ conversation.title }}</h1>
          <p class="text-sm text-base-content/70">{{ startedOn(conversation.started_at) }} · {{ conversation.situation }}</p>
        </div>
        <RouterLink
          v-if="conversation.topic_id !== null"
          class="btn btn-primary btn-sm"
          :to="{ name: 'practice', params: { id: conversation.topic_id } }"
        >
          Practice this topic again
        </RouterLink>
      </header>

      <details v-if="conversation.background" class="collapse-arrow collapse mt-3 border border-base-300 bg-base-100">
        <summary class="collapse-title text-sm font-medium">What the text was about</summary>
        <p class="collapse-content text-sm text-base-content/80">{{ conversation.background }}</p>
      </details>

      <ReviewCard v-if="conversation.review" class="mt-4" :review="conversation.review" :messages="messages" @hear="speech.speak" />
      <div v-else class="mt-4 flex flex-wrap items-center gap-3">
        <button class="btn btn-sm" :disabled="reviewing" @click="summarize">Summarize this conversation</button>
        <span v-if="reviewing" class="flex items-center gap-2 text-sm text-base-content/60">
          <MorseSignal animated /> Writing your summary…
        </span>
      </div>
      <div v-if="reviewError" role="alert" class="alert alert-error alert-soft mt-3">{{ reviewError }}</div>

      <section class="mt-4 flex flex-col gap-1" aria-label="Conversation">
        <template v-for="(message, i) in messages" :key="i">
          <div class="chat" :class="message.role === 'tutor' ? 'chat-start' : 'chat-end'">
            <div class="chat-header text-xs text-base-content/60">{{ message.role === 'tutor' ? 'Partner' : 'You' }}</div>
            <div class="chat-bubble" :class="message.role === 'learner' ? 'chat-bubble-primary' : ''">{{ message.text }}</div>
            <div v-if="message.role === 'tutor'" class="chat-footer mt-1">
              <button class="btn btn-xs" @click="speech.speak(message.text)">Hear it</button>
            </div>
            <DeliveryNote v-else-if="message.delivery" :delivery="message.delivery" />
          </div>
          <CorrectionCard v-if="message.correction" :correction="message.correction" @hear="speech.speak" />
        </template>
      </section>
    </template>

    <div v-else role="alert" class="alert alert-error mt-4">{{ error || 'This conversation could not be opened.' }}</div>
  </main>
</template>
