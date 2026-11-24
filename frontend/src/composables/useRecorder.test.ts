import { describe, expect, it } from 'vitest'
import { micProblem } from './useRecorder'

const failure = (name: string) => Object.assign(new Error('x'), { name })

describe('micProblem', () => {
  it('says that no microphone is connected when none was found', () => {
    expect(micProblem(failure('NotFoundError'))).toBe('No microphone was found. Connect one and try again.')
  })

  it('points at the privacy settings when access was refused', () => {
    expect(micProblem(failure('NotAllowedError'))).toBe(
      "Microphone access is turned off. Allow it for this app in your system's privacy settings and try again.",
    )
  })

  it('says another app may hold the microphone when it cannot be read', () => {
    expect(micProblem(failure('NotReadableError'))).toBe(
      'The microphone could not be started. Close other apps that use it and try again.',
    )
  })

  it('names any other failure, so it can be reported', () => {
    expect(micProblem(failure('AbortError'))).toBe('The microphone is not available (AbortError).')
    expect(micProblem('boom')).toBe('The microphone is not available.')
  })
})
