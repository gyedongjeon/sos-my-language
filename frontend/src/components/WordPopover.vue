<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSpeech } from '../composables/useSpeech'
import { t } from '../i18n'
import { useLookupStore } from '../stores/lookup'
import MarkedText from './MarkedText.vue'
import MorseSignal from './MorseSignal.vue'

// The explanation of the word the learner tapped, next to the word.
const lookup = useLookupStore()
const route = useRoute()
const speech = useSpeech()
const box = ref<HTMLElement | null>(null)
const WIDTH = 288
const GUTTER = 16

const headword = computed(() => lookup.found?.phrase || lookup.found?.lemma || lookup.tapped?.word || '')
// Below the word, or above it when there is no room below; never off the side of the window.
const place = computed(() => {
  const at = lookup.tapped?.at
  if (!at) return {}
  const left = Math.max(GUTTER, Math.min(at.left, window.innerWidth - WIDTH - GUTTER))
  const below = window.innerHeight - at.bottom > 220
  return below
    ? { left: `${left}px`, top: `${at.bottom + 6}px` }
    : { left: `${left}px`, bottom: `${window.innerHeight - at.top + 6}px` }
})

function close() {
  speech.stop()
  lookup.close()
}

// Closed by tapping anywhere else (another word opens its own), by Escape, and by scrolling,
// which would leave it away from its word.
function away(event: PointerEvent) {
  const on = event.target as Element | null
  if (box.value?.contains(on) || on?.closest('[data-lookup]')) return
  if (lookup.tapped) close()
}
function key(event: KeyboardEvent) {
  if (event.key === 'Escape' && lookup.tapped) close()
}
function scrolled() {
  if (lookup.tapped) close()
}
onMounted(() => {
  document.addEventListener('pointerdown', away)
  document.addEventListener('keydown', key)
  window.addEventListener('scroll', scrolled, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', away)
  document.removeEventListener('keydown', key)
  window.removeEventListener('scroll', scrolled, true)
})
watch(() => route.fullPath, close)
</script>

<template>
  <div
    v-if="lookup.tapped"
    ref="box"
    role="dialog"
    :aria-label="t('lookup.dialog')"
    class="card card-border fixed z-50 bg-base-100 text-base-content shadow-lg"
    :style="{ ...place, width: `min(${WIDTH}px, calc(100vw - ${2 * GUTTER}px))` }"
  >
    <div class="card-body gap-1 p-4 text-sm">
      <div class="flex items-start gap-2">
        <p class="text-lg font-semibold leading-snug">{{ headword }}</p>
        <button v-if="lookup.found" class="btn btn-ghost btn-xs" @click="speech.speak(headword)">{{ t('common.hearIt') }}</button>
        <button class="btn btn-ghost btn-xs btn-square" :aria-label="t('common.close')" @click="close">✕</button>
      </div>
      <p v-if="lookup.loading" class="flex items-center gap-2 text-base-content/60">
        <MorseSignal animated /> {{ t('lookup.looking') }}
      </p>
      <div v-else-if="lookup.error" role="alert" class="alert alert-error alert-soft p-2">
        {{ lookup.error }}
        <button class="btn btn-xs" @click="lookup.lookUp(lookup.tapped.word, lookup.tapped.sentence, lookup.tapped.at, lookup.tapped.piece)">
          {{ t('common.tryAgain') }}
        </button>
      </div>
      <template v-else-if="lookup.found">
        <p v-if="lookup.found.pronunciation" class="text-base-content/60">/{{ lookup.found.pronunciation }}/</p>
        <p v-if="lookup.found.phrase && lookup.found.phrase !== lookup.found.lemma" class="text-base-content/60">
          {{ lookup.found.word }} · {{ lookup.found.lemma }}
        </p>
        <p v-if="lookup.found.part_of_speech" class="text-base-content/60">{{ lookup.found.part_of_speech }}</p>
        <p class="font-medium">{{ lookup.found.meaning }}</p>
        <MarkedText
          v-if="lookup.found.translation"
          tag="p"
          class="text-base-content/70"
          :text="lookup.found.translation"
          :part="lookup.found.in_translation"
        />
        <div class="card-actions mt-1">
          <!-- Pressed again, a saved word is taken off the list. -->
          <button
            class="btn btn-xs"
            :class="lookup.found.saved === null ? 'btn-primary' : 'btn-soft btn-primary'"
            :aria-pressed="lookup.found.saved !== null"
            :disabled="lookup.saving"
            @click="lookup.toggleSaved()"
          >
            {{ lookup.found.saved === null ? t('lookup.save') : `✓ ${t('lookup.saved')}` }}
          </button>
        </div>
        <p v-if="lookup.saveError" role="alert" class="text-error">{{ lookup.saveError }}</p>
      </template>
    </div>
  </div>
</template>
