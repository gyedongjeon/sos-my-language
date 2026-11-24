<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import MorseSignal from '../components/MorseSignal.vue'
import { startedOn } from '../history'
import type { ConversationSummary } from '../types'

const conversations = ref<ConversationSummary[]>([])
const loading = ref(true)
const error = ref('')
// The conversation whose "Delete" was pressed once; deleting takes a second press.
const confirming = ref<number | null>(null)

const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

async function remove(id: number) {
  error.value = ''
  try {
    await api(`/conversations/${id}`, { method: 'DELETE' })
    conversations.value = conversations.value.filter((c) => c.id !== id)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    confirming.value = null
  }
}

onMounted(async () => {
  try {
    conversations.value = await api<ConversationSummary[]>('/conversations')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="mx-auto max-w-3xl p-4 sm:p-6">
    <h1 class="text-2xl font-semibold">History</h1>
    <p class="text-sm text-base-content/70">Your conversations, saved on this computer as you have them.</p>

    <div v-if="loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>
    <template v-else>
      <div v-if="error" role="alert" class="alert alert-error alert-soft mt-4">{{ error }}</div>

      <div v-if="!conversations.length && !error" class="card card-border mt-4 bg-base-100">
        <div class="card-body items-start">
          <p>No conversations yet. They appear here once you have said something in one.</p>
          <RouterLink class="btn btn-primary btn-sm" :to="{ name: 'home' }">Pick a topic</RouterLink>
        </div>
      </div>

      <ul class="mt-4 grid gap-3">
        <li v-for="c in conversations" :key="c.id" class="card card-border bg-base-100">
          <div class="card-body flex-row flex-wrap items-center gap-3">
            <RouterLink class="grow" :to="{ name: 'conversation', params: { id: c.id } }">
              <h2 class="card-title text-lg">{{ c.title }}</h2>
              <p class="text-sm text-base-content/60">
                {{ startedOn(c.started_at) }} · {{ count(c.turns, 'turn', 'turns') }} ·
                {{ count(c.corrections, 'correction', 'corrections') }}
              </p>
            </RouterLink>
            <template v-if="confirming === c.id">
              <button class="btn btn-error btn-sm" @click="remove(c.id)">Delete for good</button>
              <button class="btn btn-ghost btn-sm" @click="confirming = null">Keep</button>
            </template>
            <button v-else class="btn btn-ghost btn-sm" :aria-label="`Delete the conversation ${c.title}`" @click="confirming = c.id">
              Delete
            </button>
          </div>
        </li>
      </ul>
    </template>
  </main>
</template>
