<script setup lang="ts">
import { computed } from 'vue'
import { tally } from '../history'
import type { Message, Review } from '../types'

// How a whole conversation went: its numbers, and the tutor's review of it.
const props = defineProps<{ review: Review; messages: Message[] }>()
defineEmits<{ hear: [text: string] }>()

const numbers = computed(() => tally(props.messages))
</script>

<template>
  <section class="card card-border bg-base-100" aria-label="Summary">
    <div class="card-body gap-4">
      <h2 class="card-title">How it went</h2>

      <div class="stats stats-vertical bg-base-200 sm:stats-horizontal">
        <div class="stat px-4 py-2">
          <div class="stat-title">Turns</div>
          <div class="stat-value text-2xl">{{ numbers.turns }}</div>
        </div>
        <div class="stat px-4 py-2">
          <div class="stat-title">Corrections</div>
          <div class="stat-value text-2xl">{{ numbers.corrections }}</div>
        </div>
        <div v-if="numbers.clarity !== null" class="stat px-4 py-2">
          <div class="stat-title">Clarity</div>
          <div class="stat-value text-2xl">{{ numbers.clarity }}</div>
        </div>
        <div v-if="numbers.wordsPerMinute !== null" class="stat px-4 py-2">
          <div class="stat-title">Words/min</div>
          <div class="stat-value text-2xl">{{ numbers.wordsPerMinute }}</div>
        </div>
      </div>

      <p>{{ review.summary }}</p>

      <div v-if="review.strengths.length">
        <h3 class="font-semibold text-success">What went well</h3>
        <ul class="ml-5 list-disc">
          <li v-for="item in review.strengths" :key="item">{{ item }}</li>
        </ul>
      </div>

      <div v-if="review.focus.length">
        <h3 class="font-semibold text-primary">Work on next</h3>
        <ul class="ml-5 list-disc">
          <li v-for="item in review.focus" :key="item">{{ item }}</li>
        </ul>
      </div>

      <div v-if="review.phrases.length">
        <h3 class="font-semibold">Worth trying next time</h3>
        <ul class="grid gap-2">
          <li v-for="phrase in review.phrases" :key="phrase.english" class="flex flex-wrap items-center gap-x-2">
            <span class="font-medium">{{ phrase.english }}</span>
            <button class="btn btn-xs" @click="$emit('hear', phrase.english)">Hear it</button>
            <span class="basis-full text-sm text-base-content/70">{{ phrase.note }}</span>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
