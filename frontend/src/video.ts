import type { VideoLine } from './types'

/** The sentence being said at a time of the video: the last one that has started; -1 before the first. */
export function lineAt(lines: VideoLine[], time: number): number {
  let found = -1
  for (let i = 0; i < lines.length && lines[i].start <= time; i++) found = i
  return found
}

/**
 * Where the video goes on from when it plays on without stopping: where it stopped, while the
 * sentence said there is the chosen one (or none is chosen yet); otherwise the start of the
 * chosen sentence, `lead` seconds early.
 */
export function resumeFrom(lines: VideoLine[], chosen: number, time: number, lead: number): number {
  if (chosen < 0 || lineAt(lines, time) === chosen) return time
  return Math.max(0, lines[chosen].start - lead)
}

/** The sentence one step forward or back from another, kept inside the list. */
export const stepFrom = (lines: VideoLine[], index: number, step: 1 | -1): number =>
  Math.min(lines.length - 1, Math.max(0, index < 0 ? 0 : index + step))

/** A time of the video as it is written on a player: 1:05, 1:02:05. */
export function clock(seconds: number): string {
  const whole = Math.floor(seconds)
  const [h, m, s] = [Math.floor(whole / 3600), Math.floor((whole % 3600) / 60), whole % 60]
  const two = (n: number) => String(n).padStart(2, '0')
  return h ? `${h}:${two(m)}:${two(s)}` : `${m}:${two(s)}`
}

/**
 * Marks words of a sentence by clicking: the first click marks a word, the second stretches the
 * mark to another word, and the next one starts again. The mark is [first, last] word, or null.
 */
export function pick(marked: [number, number] | null, index: number): [number, number] | null {
  if (!marked || marked[0] !== marked[1]) return [index, index]
  if (marked[0] === index) return null
  return [Math.min(marked[0], index), Math.max(marked[0], index)]
}
