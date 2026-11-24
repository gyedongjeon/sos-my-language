import { onBeforeUnmount, ref, type Ref } from 'vue'

// The parts of YouTube's IFrame Player API that are used here.
interface Player {
  playVideo(): void
  pauseVideo(): void
  seekTo(seconds: number, allowSeekAhead: boolean): void
  getCurrentTime(): number
  setPlaybackRate(rate: number): void
  loadModule(name: string): void
  unloadModule(name: string): void
  setOption(module: string, option: string, value: unknown): void
  destroy(): void
}
interface PlayerOptions {
  videoId: string
  host?: string
  playerVars?: Record<string, string | number>
  events?: {
    onReady?: () => void
    onStateChange?: (event: { data: number }) => void
    onError?: (event: { data: number }) => void
  }
}
declare global {
  interface Window {
    YT?: { Player: new (element: HTMLElement, options: PlayerOptions) => Player }
    onYouTubeIframeAPIReady?: () => void
  }
}

// The player's states in which the video is running: playing, and loading more of it after a jump.
const RUNNING = [1, 3]
// How often the time of the video is read while it plays, in milliseconds.
const TICK_MS = 100
// YouTube's error codes for a video its owner does not let other pages show.
const NOT_EMBEDDABLE = [101, 150, 153]

let api: Promise<void> | null = null

/** Loads YouTube's player script once for the whole app. */
function loadApi(): Promise<void> {
  api ??= new Promise((resolve, reject) => {
    if (window.YT?.Player) return resolve()
    window.onYouTubeIframeAPIReady = () => resolve()
    const script = document.createElement('script')
    script.src = 'https://www.youtube.com/iframe_api'
    script.onerror = () => {
      api = null
      reject(new Error('YouTube could not be reached.'))
    }
    document.head.append(script)
  })
  return api
}

/**
 * YouTube's own player inside an element of the page. The video is streamed by YouTube; this
 * only steers it: play one part of the video and stop, or keep repeating it.
 */
export function useYouTubePlayer(element: Ref<HTMLElement | null>) {
  const ready = ref(false)
  const playing = ref(false)
  const time = ref(0)
  const error = ref('')
  // The part being played on its own; the video stops, or goes back, at its end.
  const part = ref<{ start: number; end: number; repeat: boolean } | null>(null)
  let player: Player | null = null
  let timer: ReturnType<typeof setInterval> | null = null

  function tick() {
    if (!player) return
    time.value = player.getCurrentTime()
    const now = part.value
    if (!now || time.value < now.end) return
    if (now.repeat) player.seekTo(now.start, true)
    else {
      // Stopped right away: YouTube reports the pause a moment later, and until then the
      // video would count as playing on into the next sentence.
      playing.value = false
      part.value = null
      player.pauseVideo()
    }
  }

  async function open(videoId: string) {
    close()
    error.value = ''
    try {
      await loadApi()
    } catch (e) {
      error.value = (e as Error).message
      return
    }
    if (!element.value || !window.YT) return
    // The player replaces the element it is given, so it gets one of its own.
    const mount = document.createElement('div')
    element.value.replaceChildren(mount)
    player = new window.YT.Player(mount, {
      videoId,
      playerVars: { rel: 0, playsinline: 1, cc_load_policy: 0 },
      events: {
        onReady: () => (ready.value = true),
        onStateChange: ({ data }) => {
          playing.value = RUNNING.includes(data)
          if (playing.value) timer ??= setInterval(tick, TICK_MS)
          else if (timer) {
            clearInterval(timer)
            timer = null
            tick()
          }
        },
        onError: ({ data }) => {
          error.value = NOT_EMBEDDABLE.includes(data)
            ? 'The owner of this video does not allow it to be played outside YouTube.'
            : `YouTube could not play this video (error ${data}).`
        },
      },
    })
  }

  /** Plays the video from `start` and stops at `end`, or goes back to `start` there when repeating. */
  function playPart(start: number, end: number, repeat = false) {
    if (!player || !ready.value) return
    part.value = { start, end, repeat }
    player.seekTo(start, true)
    player.playVideo()
  }

  function pause() {
    part.value = null
    player?.pauseVideo()
  }

  function setRate(rate: number) {
    player?.setPlaybackRate(rate)
  }

  /** Shows or hides the subtitles YouTube draws over the video. */
  function setCaptions(on: boolean) {
    if (!player) return
    if (on) player.loadModule('captions')
    else {
      // Choosing no track turns the subtitles off; unloading keeps them from coming back.
      player.setOption('captions', 'track', {})
      player.unloadModule('captions')
    }
  }

  function close() {
    if (timer) clearInterval(timer)
    timer = null
    player?.destroy()
    player = null
    part.value = null
    ready.value = false
    playing.value = false
    time.value = 0
  }

  onBeforeUnmount(close)
  return { ready, playing, time, error, part, open, playPart, pause, setRate, setCaptions, close }
}
