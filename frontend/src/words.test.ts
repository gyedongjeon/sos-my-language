import { describe, expect, it } from 'vitest'
import { splitWords } from './words'

const words = (text: string) => splitWords(text).filter((p) => p.word).map((p) => p.text)

describe('splitWords', () => {
  it('keeps every character of the text, in order', () => {
    const text = 'Not heard: “four lobes” (heard “of her roles”).'
    expect(splitWords(text).map((p) => p.text).join('')).toBe(text)
  })

  it('makes a word of each run of letters and leaves out spaces and punctuation', () => {
    expect(splitWords('It involves the cortex.')).toEqual([
      { text: 'It', word: true },
      { text: ' ', word: false },
      { text: 'involves', word: true },
      { text: ' ', word: false },
      { text: 'the', word: true },
      { text: ' ', word: false },
      { text: 'cortex', word: true },
      { text: '.', word: false },
    ])
  })

  it('keeps short forms and words joined by a hyphen whole', () => {
    expect(words("I don't know a well-known café’s name")).toEqual(['I', "don't", 'know', 'a', 'well-known', 'café’s', 'name'])
  })

  it('knows the letters of other alphabets', () => {
    expect(words('Die Häuser sind groß.')).toEqual(['Die', 'Häuser', 'sind', 'groß'])
  })

  it('does not make a word of a number', () => {
    expect(words('At 8 or 10am')).toEqual(['At', 'or', '10am'])
  })
})
