import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useSettingsStore } from '../stores/settings'
import en from './en'
import { languageName, modelName, PAGE_LANGUAGES, t, tc, voiceLabel } from './index'
import ko from './ko'

beforeEach(() => setActivePinia(createPinia()))

const yours = (language: string) => (useSettingsStore().feedbackLanguage = language)

describe('the texts of the pages', () => {
  it('are in English until the learner has another language', () => {
    expect(t('nav.history')).toBe('History')
  })

  it("are in the learner's language when the pages are written in it", () => {
    yours('Korean')
    expect(t('nav.history')).toBe('기록')
  })

  it('are in English for a language the pages are not written in', () => {
    yours('Japanese')
    expect(PAGE_LANGUAGES).not.toContain('Japanese')
    expect(t('nav.history')).toBe('History')
  })

  it('have their names filled in', () => {
    expect(t('drill.sayIn', { language: 'German' })).toBe('Say it in German')
    yours('Korean')
    expect(t('drill.sayIn', { language: '독일어' })).toBe('독일어로 말하기')
  })

  it('say one or many by the number', () => {
    expect(t('history.turns', { n: 1 })).toBe('1 turn')
    expect(t('history.turns', { n: 3 })).toBe('3 turns')
    yours('Korean')
    expect(t('history.turns', { n: 1 })).toBe('1번 말함')
    expect(t('history.turns', { n: 3 })).toBe('3번 말함')
  })

  it('name the languages taught and the speech models', () => {
    expect(languageName('de', 'German')).toBe('German')
    expect(modelName('voice', 'Partner\u2019s voice')).toBe("Partner's voice")
    yours('Korean')
    expect(languageName('de', 'German')).toBe('독일어')
    expect(modelName('speech-to-text', 'Speech recognition')).toBe('음성 인식')
    // One the pages do not know yet keeps the name the backend gave it.
    expect(languageName('es', 'Spanish')).toBe('Spanish')
  })

  it('have every text in Korean, with the same names to fill in', () => {
    const names = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()
    expect(Object.keys(ko).sort()).toEqual(Object.keys(en).sort())
    for (const key of Object.keys(en) as (keyof typeof en)[]) {
      expect(ko[key].trim(), key).not.toBe('')
      expect(new Set(names(ko[key])), key).toEqual(new Set(names(en[key])))
    }
  })
})

describe('the built-in topics and pattern notes', () => {
  it("are shown in the learner's language", () => {
    expect(tc('Small talk')).toBe('Small talk')
    yours('Korean')
    expect(tc('Small talk')).toBe('가벼운 대화')
    expect(tc('Everyday')).toBe('일상')
    expect(tc('Giving advice')).toBe('조언할 때')
  })

  it('say what a voice is like, and leave its name', () => {
    expect(voiceLabel('Emma · British · female')).toBe('Emma · British · female')
    yours('Korean')
    expect(voiceLabel('Emma · British · female')).toBe('Emma · 영국식 · 여성')
  })

  it('leave what the learner wrote as it is', () => {
    yours('Korean')
    expect(tc('Renting a car in Lisbon')).toBe('Renting a car in Lisbon')
  })
})
