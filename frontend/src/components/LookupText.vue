<script setup lang="ts">
import { computed } from 'vue'
import { t } from '../i18n'
import { useLookupStore } from '../stores/lookup'
import { splitWords } from '../words'

// A sentence in the language being learned whose words the learner can tap to see what they mean.
const props = defineProps<{ text: string }>()
const lookup = useLookupStore()
const pieces = computed(() => splitWords(props.text))
// The tapped word, by its place among the pieces, while its explanation is open.
const tapped = computed(() => (lookup.tapped?.sentence === props.text ? lookup.tapped.piece : null))

function tap(event: MouseEvent, piece: number) {
  // A sentence may be inside something that reacts to a click itself.
  event.stopPropagation()
  if (tapped.value === piece) return lookup.close()
  const { left, top, bottom } = (event.currentTarget as HTMLElement).getBoundingClientRect()
  void lookup.lookUp(pieces.value[piece].text, props.text, { left, top, bottom }, piece)
}
</script>

<template>
  <span
    ><template v-for="(piece, i) in pieces" :key="i"
      ><button
        v-if="piece.word"
        type="button"
        data-lookup
        class="cursor-pointer rounded-sm decoration-current/30 decoration-dotted underline-offset-4 hover:bg-primary/15 hover:underline"
        :class="tapped === i ? 'bg-primary/20' : ''"
        :aria-label="t('lookup.word', { word: piece.text })"
        :aria-expanded="tapped === i"
        @click="tap($event, i)"
        >{{ piece.text }}</button
      ><template v-else>{{ piece.text }}</template></template
    ></span
  >
</template>
