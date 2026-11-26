<script setup lang="ts">
import LookupText from '../components/LookupText.vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import CorrectionCard from '../components/CorrectionCard.vue'
import DeliveryNote from '../components/DeliveryNote.vue'
import MorseSignal from '../components/MorseSignal.vue'
import ReviewCard from '../components/ReviewCard.vue'
import { useSpeech } from '../composables/useSpeech'
import { fromSaved, startedOn } from '../history'
import type { Review, SavedConversation } from '../types'
import { useSettingsStore } from '../stores/settings'
import { t, tc } from '../i18n'

const settings = useSettingsStore()

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
    reviewError.value = t('practice.summaryFailed', { error: (e as Error).message })
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
    const found = await api<SavedConversation>(`/conversations/${props.id}`)
    // Its lines are heard, and its summary written, in the language it was held in.
    await settings.practise(found.language)
    conversation.value = found
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
    <RouterLink class="link text-sm" :to="{ name: 'history' }">{{ t('history.back') }}</RouterLink>

    <div v-if="loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>

    <template v-else-if="conversation">
      <header class="mt-2 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 class="text-2xl font-semibold">{{ tc(conversation.title) }}</h1>
          <p class="text-sm text-base-content/70">{{ startedOn(conversation.started_at) }} · {{ tc(conversation.situation) }}</p>
        </div>
        <RouterLink
          v-if="conversation.topic_id !== null"
          class="btn btn-primary btn-sm"
          :to="{ name: 'practice', params: { id: conversation.topic_id } }"
        >
          {{ t('history.again') }}
        </RouterLink>
      </header>

      <details v-if="conversation.background" class="collapse-arrow collapse mt-3 border border-base-300 bg-base-100">
        <summary class="collapse-title text-sm font-medium">{{ t('practice.background') }}</summary>
        <p class="collapse-content text-sm text-base-content/80">{{ conversation.background }}</p>
      </details>

      <ReviewCard v-if="conversation.review" class="mt-4" :review="conversation.review" :messages="messages" @hear="speech.speak" />
      <div v-else class="mt-4 flex flex-wrap items-center gap-3">
        <button class="btn btn-sm" :disabled="reviewing" @click="summarize">{{ t('history.summarize') }}</button>
        <span v-if="reviewing" class="flex items-center gap-2 text-sm text-base-content/60">
          <MorseSignal animated /> {{ t('practice.writingSummary') }}
        </span>
      </div>
      <div v-if="reviewError" role="alert" class="alert alert-error alert-soft mt-3">{{ reviewError }}</div>

      <section class="mt-4 flex flex-col gap-1" :aria-label="t('practice.conversation')">
        <template v-for="(message, i) in messages" :key="i">
          <div class="chat" :class="message.role === 'tutor' ? 'chat-start' : 'chat-end'">
            <div class="chat-header text-xs text-base-content/60">{{ message.role === 'tutor' ? t('common.partner') : t('common.you') }}</div>
            <div class="chat-bubble" :class="message.role === 'learner' ? 'chat-bubble-primary' : ''">
              <LookupText v-if="message.role === 'tutor'" :text="message.text" /><template v-else>{{ message.text }}</template>
            </div>
            <div v-if="message.role === 'tutor'" class="chat-footer mt-1">
              <button class="btn btn-xs" @click="speech.speak(message.text)">{{ t('common.hearIt') }}</button>
            </div>
            <DeliveryNote v-else-if="message.delivery" :delivery="message.delivery" />
          </div>
          <CorrectionCard v-if="message.correction" :correction="message.correction" @hear="speech.speak" />
        </template>
      </section>
    </template>

    <div v-else role="alert" class="alert alert-error mt-4">{{ error || t('history.cannotOpen') }}</div>
  </main>
</template>
