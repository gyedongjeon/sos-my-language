<script setup lang="ts">
import { modelName, t } from '../i18n'
import { megabytes, percent, useModelsStore } from '../stores/models'

// Shown under the navigation bar while the speech models of a language download, the first time it is practised.
const models = useModelsStore()
</script>

<template>
  <!-- The alert lays its children out in a row, so each message is a single child. -->
  <div v-if="models.active.length" role="status" class="alert alert-info alert-soft mx-auto mt-4 max-w-3xl">
    <div class="grid w-full gap-3">
      <div>
        <p class="font-semibold">{{ t('downloads.title') }}</p>
        <p class="text-sm">
          {{ t('downloads.body') }}
        </p>
      </div>
      <div v-for="m in models.active" :key="m.id" class="text-sm">
        <div class="flex justify-between gap-2">
          <span>{{ modelName(m.id, m.label) }}</span>
          <span class="tabular-nums">
            <template v-if="percent(m) !== null">{{ percent(m) }}% · </template>{{ megabytes(m.downloaded)
            }}<template v-if="m.total"> / {{ megabytes(m.total) }}</template> MB
          </span>
        </div>
        <!-- Without a value the bar shows that something is happening, not how much. -->
        <progress
          class="progress progress-primary w-full"
          :value="percent(m) ?? undefined"
          max="100"
          :aria-label="t('downloads.of', { name: modelName(m.id, m.label) })"
        ></progress>
      </div>
    </div>
  </div>
  <div v-else-if="models.failed.length" role="alert" class="alert alert-error alert-soft mx-auto mt-4 max-w-3xl">
    <div>
      <p class="font-semibold">{{ t('downloads.failed') }}</p>
      <p v-for="m in models.failed" :key="m.id" class="text-sm">{{ modelName(m.id, m.label) }}: {{ m.error }}</p>
    </div>
    <button class="btn btn-sm" @click="models.start()">{{ t('common.tryAgain') }}</button>
  </div>
</template>
