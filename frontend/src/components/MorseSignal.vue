<script setup lang="ts">
// "SOS" in Morse code (··· ––– ···): the brand motif, and the loading indicator when animated.
defineProps<{ animated?: boolean }>()

const SIGNAL = [...'...---...'].map((mark) => mark === '-')
</script>

<template>
  <span
    class="inline-flex items-center gap-1 text-primary"
    :role="animated ? 'status' : undefined"
    :aria-label="animated ? 'Loading' : undefined"
    :aria-hidden="animated ? undefined : true"
  >
    <span
      v-for="(dash, i) in SIGNAL"
      :key="i"
      class="h-1.5 rounded-full bg-current"
      :class="[dash ? 'w-4' : 'w-1.5', i % 3 === 0 && i ? 'ml-1.5' : '', animated ? 'animate-pulse' : '']"
      :style="animated ? { animationDelay: `${i * 120}ms` } : undefined"
    ></span>
  </span>
</template>
