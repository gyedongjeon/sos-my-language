<script setup lang="ts">
import { onMounted, ref } from 'vue'
import MorseSignal from '../components/MorseSignal.vue'
import { usePatternsStore } from '../stores/patterns'
import { useSettingsStore } from '../stores/settings'
import { t, tc } from '../i18n'

const settings = useSettingsStore()

// The sentence patterns, one CEFR level at a time, with how the last round of each went.
const store = usePatternsStore()
// The own pattern whose "Delete" was pressed once; deleting takes a second press.
const confirming = ref<string | null>(null)

async function remove(id: string) {
  await store.remove(id)
  confirming.value = null
}

onMounted(() => store.load())
</script>

<template>
  <main class="mx-auto max-w-3xl p-4 sm:p-6">
    <h1 class="text-2xl font-semibold">{{ t('nav.patterns') }}</h1>
    <p class="text-sm text-base-content/70">
      {{ t('patterns.intro', { language: settings.learningName }) }}
    </p>

    <div v-if="store.loading" class="flex justify-center py-16">
      <MorseSignal animated />
    </div>
    <div v-else-if="store.error" role="alert" class="alert alert-error alert-soft mt-4">{{ store.error }}</div>

    <template v-else>
      <div class="mt-4 flex flex-wrap gap-2" role="tablist" :aria-label="t('common.levels')">
        <button
          v-for="level in store.levels"
          :key="level"
          role="tab"
          :aria-selected="level === store.active"
          class="btn btn-sm rounded-full"
          :class="level === store.active ? 'btn-primary' : 'btn-ghost bg-base-100'"
          @click="store.level = level"
        >
          {{ tc(level) }}
        </button>
      </div>

      <ul class="mt-3 grid gap-3">
        <li v-for="p in store.shown" :key="p.id" class="card card-border bg-base-100 transition hover:border-primary">
          <div class="card-body flex-row flex-wrap items-center gap-3">
            <RouterLink class="flex grow basis-64 items-center gap-4" :to="{ name: 'pattern', params: { id: p.id } }">
              <div class="grow">
                <h2 class="card-title text-lg">{{ p.pattern }}</h2>
                <p class="text-sm text-base-content/60">{{ tc(p.use) }}</p>
                <p v-if="p.custom" class="mt-1 text-sm italic text-base-content/60">“{{ p.example }}”</p>
              </div>
              <span
                v-if="p.sessions"
                class="badge badge-soft whitespace-nowrap"
                :class="p.last_correct === p.last_total ? 'badge-success' : 'badge-neutral'"
                :title="t('patterns.practised', { n: p.sessions })"
              >
                {{ p.last_correct }}/{{ p.last_total }}
              </span>
              <span aria-hidden="true" class="text-2xl text-primary">›</span>
            </RouterLink>
            <template v-if="p.custom">
              <RouterLink
                v-if="p.video !== null"
                class="btn btn-ghost btn-sm"
                :to="{ name: 'video', params: { id: p.video }, query: { line: p.position ?? 0 } }"
              >
                {{ t('patterns.inVideo') }}
              </RouterLink>
              <template v-if="confirming === p.id">
                <button class="btn btn-error btn-sm" @click="remove(p.id)">{{ t('common.deleteForGood') }}</button>
                <button class="btn btn-ghost btn-sm" @click="confirming = null">{{ t('common.keep') }}</button>
              </template>
              <button v-else class="btn btn-ghost btn-sm" :aria-label="t('patterns.delete', { pattern: p.pattern })" @click="confirming = p.id">
                {{ t('common.delete') }}
              </button>
            </template>
          </div>
        </li>
      </ul>
    </template>
  </main>
</template>
