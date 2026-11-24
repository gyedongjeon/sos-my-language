<script setup lang="ts">
import { t } from '../i18n'
import type { Delivery } from '../types'

// How a line was spoken: clarity, pace, and the words that were hard to recognize.
defineProps<{ delivery: Delivery }>()
</script>

<template>
  <div class="chat-footer mt-1 text-xs text-base-content/60">
    {{ t('delivery.clarity', { n: delivery.clarity })
    }}<template v-if="delivery.wordsPerMinute">{{ t('delivery.pace', { n: delivery.wordsPerMinute }) }}</template
    ><template v-if="delivery.unclearWords.length">{{
      t('delivery.unclear', { words: delivery.unclearWords.join(', ') })
    }}</template>
  </div>
</template>
