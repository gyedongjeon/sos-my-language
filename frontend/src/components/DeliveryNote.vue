<script setup lang="ts">
import type { Delivery } from '../types'

// How a line was spoken: clarity, pace, and the words that were hard to recognize.
defineProps<{ delivery: Delivery }>()
</script>

<template>
  <div class="chat-footer mt-1 text-xs text-base-content/60">
    Clarity {{ delivery.clarity }}
    <template v-if="delivery.wordsPerMinute"> · {{ delivery.wordsPerMinute }} words/min</template>
    <template v-if="delivery.unclearWords.length"> · unclear: {{ delivery.unclearWords.join(', ') }}</template>
  </div>
</template>
