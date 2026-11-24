import { describe, expect, it } from 'vitest'
import { clock, lineAt, pick, stepFrom } from './video'

const LINES = [
  { start: 7, end: 10, text: 'One.' },
  { start: 10, end: 14.5, text: 'Two.' },
  { start: 20, end: 24, text: 'Three.' },
]

describe('lineAt', () => {
  it('finds the sentence being said at a time', () => {
    expect(lineAt(LINES, 7)).toBe(0)
    expect(lineAt(LINES, 9.99)).toBe(0)
    expect(lineAt(LINES, 10)).toBe(1)
    expect(lineAt(LINES, 23)).toBe(2)
  })

  it('stays on the last sentence said during a pause and after the end', () => {
    expect(lineAt(LINES, 17)).toBe(1)
    expect(lineAt(LINES, 99)).toBe(2)
  })

  it('has no sentence before the first one', () => {
    expect(lineAt(LINES, 3)).toBe(-1)
    expect(lineAt([], 3)).toBe(-1)
  })
})

describe('stepFrom', () => {
  it('goes to the next or the previous sentence and stops at the ends', () => {
    expect(stepFrom(LINES, 0, 1)).toBe(1)
    expect(stepFrom(LINES, 2, 1)).toBe(2)
    expect(stepFrom(LINES, 1, -1)).toBe(0)
    expect(stepFrom(LINES, 0, -1)).toBe(0)
  })

  it('starts at the first sentence when none was chosen yet', () => {
    expect(stepFrom(LINES, -1, 1)).toBe(0)
    expect(stepFrom(LINES, -1, -1)).toBe(0)
  })
})

describe('clock', () => {
  it('writes seconds as minutes and seconds, with hours when needed', () => {
    expect(clock(7.4)).toBe('0:07')
    expect(clock(65)).toBe('1:05')
    expect(clock(3725)).toBe('1:02:05')
  })
})

describe('pick', () => {
  it('marks one word first, then stretches the mark to a second word in either direction', () => {
    expect(pick(null, 3)).toEqual([3, 3])
    expect(pick([3, 3], 6)).toEqual([3, 6])
    expect(pick([3, 3], 1)).toEqual([1, 3])
  })

  it('starts again once a stretch of words is marked', () => {
    expect(pick([3, 6], 4)).toEqual([4, 4])
  })

  it('takes the mark off when the one marked word is picked again', () => {
    expect(pick([3, 3], 3)).toBeNull()
  })
})
