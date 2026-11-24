<script setup lang="ts">
import { t } from '../i18n'
import type { Correction } from '../types'

// The tutor's fix for one thing the learner said: what was said, the better version, and why.
defineProps<{ correction: Correction }>()
defineEmits<{ hear: [text: string] }>()
</script>

<template>
  <div class="card card-border ml-auto max-w-[85%] bg-base-100">
    <div class="card-body gap-1 p-3 text-sm">
      <p class="text-base-content/60 line-through">{{ correction.original }}</p>
      <p class="font-medium text-success">{{ correction.improved }}</p>
      <p class="text-base-content/70">{{ correction.explanation }}</p>
      <div>
        <button class="btn btn-xs" @click="$emit('hear', correction.improved)">{{ t('common.hearIt') }}</button>
      </div>
    </div>
  </div>
</template>
