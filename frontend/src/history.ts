import type { Message, SavedMessage } from './types'

/** A line as the backend stores it, in the shape the conversation pages show. */
export function fromSaved(saved: SavedMessage): Message {
  const spoken = saved.delivery
  return {
    role: saved.role,
    text: saved.text,
    correction: saved.correction,
    delivery: spoken && {
      clarity: spoken.clarity,
      unclearWords: spoken.unclear_words,
      wordsPerMinute: spoken.words_per_minute,
    },
  }
}

/** When a conversation was held, in the reader's own date format. */
export const startedOn = (startedAt: string) =>
  new Date(startedAt).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })

const average = (numbers: number[]) =>
  numbers.length ? Math.round(numbers.reduce((sum, n) => sum + n, 0) / numbers.length) : null

/** A conversation in numbers: how often the learner spoke and was corrected, and how it sounded on average. */
export function tally(messages: Message[]) {
  const said = messages.filter((m) => m.role === 'learner')
  const measured = said.flatMap((m) => (m.delivery ? [m.delivery] : []))
  return {
    turns: said.length,
    corrections: said.filter((m) => m.correction).length,
    clarity: average(measured.map((d) => d.clarity)),
    wordsPerMinute: average(measured.flatMap((d) => (d.wordsPerMinute ? [d.wordsPerMinute] : []))),
  }
}
