<script setup lang="ts">
import { megabytes, percent, useModelsStore } from '../stores/models'

// Shown under the navigation bar while the speech models download on the first launch.
const models = useModelsStore()
</script>

<template>
  <!-- The alert lays its children out in a row, so each message is a single child. -->
  <div v-if="models.active.length" role="status" class="alert alert-info alert-soft mx-auto mt-4 max-w-3xl">
    <div class="grid w-full gap-3">
      <div>
        <p class="font-semibold">Downloading the speech models</p>
        <p class="text-sm">
          This happens once. You can keep using the app: until it is done, your partner speaks with the system
          voice and the first thing you say waits for speech recognition.
        </p>
      </div>
      <div v-for="m in models.active" :key="m.id" class="text-sm">
        <div class="flex justify-between gap-2">
          <span>{{ m.label }}</span>
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
          :aria-label="`${m.label} download`"
        ></progress>
      </div>
    </div>
  </div>
  <div v-else-if="models.failed.length" role="alert" class="alert alert-error alert-soft mx-auto mt-4 max-w-3xl">
    <div>
      <p class="font-semibold">A speech model could not be downloaded</p>
      <p v-for="m in models.failed" :key="m.id" class="text-sm">{{ m.label }}: {{ m.error }}</p>
    </div>
    <button class="btn btn-sm" @click="models.start()">Try again</button>
  </div>
</template>
