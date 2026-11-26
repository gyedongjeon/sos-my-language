import { describe, expect, it } from 'vitest'
import { markPart, splitWords } from './words'

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

describe('markPart', () => {
  it('marks the tapped word where it stands as a word, not inside another', () => {
    expect(markPart('A cat and a dog.', 'a', true)).toEqual([
      { text: 'A', marked: true },
      { text: ' cat and a dog.', marked: false },
    ])
    expect(markPart('Cats, not the cat.', 'cat', true)).toEqual([
      { text: 'Cats, not the ', marked: false },
      { text: 'cat', marked: true },
      { text: '.', marked: false },
    ])
  })

  it('marks words of a translation as they are written in it', () => {
    expect(markPart('그것은 피질의 네 엽 모두를 포함합니다.', '네 엽')).toEqual([
      { text: '그것은 피질의 ', marked: false },
      { text: '네 엽', marked: true },
      { text: ' 모두를 포함합니다.', marked: false },
    ])
  })

  it('leaves the text unmarked when the part is not in it', () => {
    expect(markPart('Der Film fängt an.', 'fangen', true)).toEqual([{ text: 'Der Film fängt an.', marked: false }])
    expect(markPart('영화가 시작합니다.', '')).toEqual([{ text: '영화가 시작합니다.', marked: false }])
  })
})
