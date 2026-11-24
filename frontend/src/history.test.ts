import { describe, expect, it } from 'vitest'
import { fromSaved, tally } from './history'

describe('fromSaved', () => {
  it('turns a saved line into one the conversation pages show', () => {
    const correction = { original: 'I go', improved: 'I went', explanation: 'Past tense.' }
    const saved = {
      role: 'learner' as const,
      text: 'I go to the beach.',
      correction,
      delivery: { clarity: 82, unclear_words: ['beach'], words_per_minute: 110 },
    }
    expect(fromSaved(saved)).toEqual({
      role: 'learner',
      text: 'I go to the beach.',
      correction,
      delivery: { clarity: 82, unclearWords: ['beach'], wordsPerMinute: 110 },
    })
  })

  it('keeps a line that was not measured or corrected as it is', () => {
    const saved = { role: 'tutor' as const, text: 'How was your week?', correction: null, delivery: null }
    expect(fromSaved(saved)).toEqual({ role: 'tutor', text: 'How was your week?', correction: null, delivery: null })
  })
})

describe('tally', () => {
  const spoken = (clarity: number, wordsPerMinute: number | null) => ({ clarity, unclearWords: [], wordsPerMinute })

  it('counts the learner’s turns and corrections, and averages how they were spoken', () => {
    const correction = { original: 'I go', improved: 'I went', explanation: 'Past tense.' }
    const messages = [
      { role: 'tutor' as const, text: 'How was your week?' },
      { role: 'learner' as const, text: 'I go to the beach.', correction, delivery: spoken(80, 100) },
      { role: 'tutor' as const, text: 'Nice!' },
      { role: 'learner' as const, text: 'With my friend.', correction: null, delivery: spoken(91, null) },
      { role: 'learner' as const, text: 'It was fun.', correction: null, delivery: null },
    ]
    expect(tally(messages)).toEqual({ turns: 3, corrections: 1, clarity: 86, wordsPerMinute: 100 })
  })

  it('has no averages when nothing was measured', () => {
    expect(tally([{ role: 'tutor', text: 'Hi!' }])).toEqual({ turns: 0, corrections: 0, clarity: null, wordsPerMinute: null })
  })
})
