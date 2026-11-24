import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useYouTubePlayer } from './useYouTubePlayer'

const PLAYING = 1

// A stand-in for YouTube's player: it reports the time it is given and hands back its events.
class FakePlayer {
  static last: FakePlayer
  now = 0
  paused = false
  events: { onReady?: () => void; onStateChange?: (event: { data: number }) => void }
  constructor(_element: unknown, options: { events: FakePlayer['events'] }) {
    this.events = options.events
    FakePlayer.last = this
  }
  playVideo() {}
  pauseVideo() {
    this.paused = true
  }
  seekTo(seconds: number) {
    this.now = seconds
  }
  getCurrentTime() {
    return this.now
  }
  setPlaybackRate() {}
  loadModule() {}
  unloadModule() {}
  setOption() {}
  destroy() {}
}

async function openedPlayer() {
  const player = useYouTubePlayer(ref({ replaceChildren() {} } as unknown as HTMLElement))
  await player.open('video')
  FakePlayer.last.events.onReady?.()
  return player
}

describe('useYouTubePlayer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal('window', { YT: { Player: FakePlayer } })
    vi.stubGlobal('document', { createElement: () => ({}) })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('counts the video as stopped as soon as a part ends, before YouTube reports the pause', async () => {
    const player = await openedPlayer()
    player.playPart(27, 30)
    FakePlayer.last.events.onStateChange?.({ data: PLAYING })

    FakePlayer.last.now = 30.05
    vi.advanceTimersByTime(100)

    expect(FakePlayer.last.paused).toBe(true)
    expect(player.part.value).toBeNull()
    expect(player.playing.value).toBe(false)
  })
})
