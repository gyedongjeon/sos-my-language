import { defineStore } from 'pinia'
import { api } from '../api'
import type { ModelStatus } from '../types'

/** How often the page asks for progress while something is downloading. */
export const POLL_MS = 2000

/** How far a download is, 0-100, or null while its size is unknown. */
export const percent = (model: ModelStatus): number | null =>
  model.total ? Math.min(100, Math.round((100 * model.downloaded) / model.total)) : null

export const megabytes = (bytes: number) => Math.round(bytes / 1_000_000)

// The speech models (several hundred MB) are downloaded once, on the first launch.
export const useModelsStore = defineStore('models', {
  state: () => ({
    models: [] as ModelStatus[],
    timer: null as ReturnType<typeof setTimeout> | null,
  }),
  getters: {
    active: (s): ModelStatus[] => s.models.filter((m) => m.state === 'downloading'),
    failed: (s): ModelStatus[] => s.models.filter((m) => m.state === 'error'),
    byId: (s) => (id: ModelStatus['id']): ModelStatus | null => s.models.find((m) => m.id === id) ?? null,
  },
  actions: {
    /** Start downloading whatever is missing; called when the app opens and to try again. */
    async start() {
      try {
        this.models = await api<ModelStatus[]>('/models/download', { method: 'POST' })
      } catch {
        // The models are also downloaded when first needed, so this is not worth an error.
      }
      this.follow()
    },
    /** Look again now: a download may have started without this page asking for it. */
    async check() {
      try {
        this.models = await api<ModelStatus[]>('/models')
      } catch {
        // Keep what is shown; the next look will correct it.
      }
      this.follow()
    },
    /** Keep looking for as long as something is downloading. */
    follow() {
      if (this.timer || !this.active.length) return
      this.timer = setTimeout(async () => {
        this.timer = null
        try {
          this.models = await api<ModelStatus[]>('/models')
        } catch {
          // One failed request must not stop the progress display; try again next time.
          this.timer = setTimeout(() => {
            this.timer = null
            void this.check()
          }, POLL_MS)
          return
        }
        this.follow()
      }, POLL_MS)
    },
  },
})
