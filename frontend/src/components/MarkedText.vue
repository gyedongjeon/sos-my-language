<script setup lang="ts">
import { computed } from 'vue'
import { markPart } from '../words'

// A text with a word of it in the accent color: the word saved in its sentence, or the words of
// a translation that stand for it.
const props = withDefaults(defineProps<{ text: string; part: string; whole?: boolean; tag?: string }>(), {
  whole: false,
  tag: 'span',
})
const pieces = computed(() => markPart(props.text, props.part, props.whole))
</script>

<template>
  <component :is="tag"
    ><template v-for="(piece, i) in pieces" :key="i"
      ><mark v-if="piece.marked" class="bg-transparent font-semibold text-primary">{{ piece.text }}</mark
      ><template v-else>{{ piece.text }}</template></template
    ></component
  >
</template>
