<script setup lang="ts">
import { computed } from 'vue'
import { markPart } from '../words'

// A translation with the words of it that stand for a tapped word in the accent color.
const props = withDefaults(defineProps<{ text: string; part: string; tag?: string }>(), { tag: 'span' })
const pieces = computed(() => markPart(props.text, props.part))
</script>

<template>
  <component :is="tag"
    ><template v-for="(piece, i) in pieces" :key="i"
      ><mark v-if="piece.marked" class="bg-transparent font-semibold text-primary">{{ piece.text }}</mark
      ><template v-else>{{ piece.text }}</template></template
    ></component
  >
</template>
