import { ref } from 'vue'

/** Why recording could not start, in words the learner can act on. */
export function micProblem(failure: unknown): string {
  const name = failure instanceof Error ? failure.name : ''
  if (name === 'NotFoundError') return 'No microphone was found. Connect one and try again.'
  if (name === 'NotAllowedError') {
    return "Microphone access is turned off. Allow it for this app in your system's privacy settings and try again."
  }
  if (name === 'NotReadableError') return 'The microphone could not be started. Close other apps that use it and try again.'
  return name ? `The microphone is not available (${name}).` : 'The microphone is not available.'
}

// Records the microphone. The stream is opened on the first recording and kept until
// release(), so later recordings start at once.
export function useRecorder() {
  const recording = ref(false)
  let stream: MediaStream | null = null
  let recorder: MediaRecorder | null = null
  let chunks: Blob[] = []

  /** Rejects when the microphone is unavailable or access to it was denied. */
  async function start() {
    if (recording.value) return
    stream ??= await navigator.mediaDevices.getUserMedia({ audio: true })
    chunks = []
    recorder = new MediaRecorder(stream)
    recorder.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data)
    }
    recorder.start()
    recording.value = true
  }

  /** Resolves with the recorded audio, or null when nothing was recorded. */
  function stop(): Promise<Blob | null> {
    return new Promise((resolve) => {
      const current = recorder
      recorder = null
      recording.value = false
      if (!current || current.state === 'inactive') return resolve(null)
      current.onstop = () => resolve(chunks.length ? new Blob(chunks, { type: current.mimeType }) : null)
      current.stop()
    })
  }

  /** Stops recording and turns the microphone off. */
  function release() {
    void stop()
    stream?.getTracks().forEach((track) => track.stop())
    stream = null
  }

  return { recording, start, stop, release }
}
