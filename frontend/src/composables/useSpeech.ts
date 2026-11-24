import { ref } from 'vue'

// Reads text aloud with the backend's local Kokoro voice, falling back to the browser's
// built-in voice (Web Speech API) when the backend cannot produce audio.
export function useSpeech(lang = 'en-US') {
  const browserVoice = 'speechSynthesis' in window
  const speaking = ref(false)
  let audio: HTMLAudioElement | null = null
  let audioUrl: string | null = null
  // Bumped on every speak()/stop() so a slow, superseded request never starts playing.
  let request = 0

  function release() {
    audio?.pause()
    audio = null
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    audioUrl = null
  }

  function stop() {
    request++
    release()
    if (browserVoice) window.speechSynthesis.cancel()
    speaking.value = false
  }

  function speakWithBrowser(text: string) {
    if (!browserVoice) {
      speaking.value = false
      return
    }
    const utter = new SpeechSynthesisUtterance(text)
    utter.lang = lang
    utter.rate = 0.95
    utter.onend = utter.onerror = () => (speaking.value = false)
    window.speechSynthesis.speak(utter)
  }

  async function speak(text: string) {
    if (!text) return
    stop()
    const mine = request
    speaking.value = true
    try {
      const res = await fetch('/api/speech', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      if (mine !== request) return
      audioUrl = URL.createObjectURL(blob)
      audio = new Audio(audioUrl)
      audio.onended = () => {
        if (mine === request) stop()
      }
      await audio.play()
    } catch {
      // Backend voice unavailable, or the browser blocked playback: use the built-in voice.
      if (mine !== request) return
      release()
      speakWithBrowser(text)
    }
  }

  return { supported: true, speaking, speak, stop }
}
