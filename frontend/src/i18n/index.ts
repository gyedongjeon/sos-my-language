import { getActivePinia } from 'pinia'
import { useSettingsStore } from '../stores/settings'
import contentKo from './content.ko.json'
import en from './en'
import ko from './ko'

/** A text of the pages, by its key in `en.ts`. */
export type MessageKey = keyof typeof en

// The languages the pages are written in, by the name the learner's language is saved under
// (see LANGUAGES in the settings store). Any other language is shown the English pages. To add
// one, write a file like `ko.ts` (and `content.ko.json`) and list it here.
const MESSAGES: Record<string, Record<MessageKey, string>> = { English: en, Korean: ko }
// The built-in topics, categories, and pattern notes, which the backend keeps in English, by
// their English text.
const CONTENT: Record<string, Record<string, string>> = { Korean: contentKo }

/** The names of the learner's languages the pages are written in. */
export const PAGE_LANGUAGES = Object.keys(MESSAGES)

// Read while a page is drawn, so the page is drawn again when the learner's language changes.
// English where there is no store to ask (a function used on its own, as in a test).
const language = () => (getActivePinia() ? useSettingsStore().feedbackLanguage : 'English')

/**
 * A text of the pages in the learner's language, with `{name}` filled in from `values`. A text
 * written as "one | many" is chosen by `values.n`.
 */
export function t(key: MessageKey, values: Record<string, string | number> = {}): string {
  let text = (MESSAGES[language()] ?? en)[key] ?? en[key]
  const forms = text.split(' | ')
  if (forms.length === 2) text = forms[values.n === 1 ? 0 : 1]
  return text.replace(/\{(\w+)\}/g, (whole, name: string) => (name in values ? String(values[name]) : whole))
}

/** A built-in text of the backend (a topic's title, a category, what a pattern is for) in the
 * learner's language; anything else, such as a topic of the learner's own, as it is. */
export function tc(text: string): string {
  return CONTENT[language()]?.[text] ?? text
}

/** A language the app teaches, named in the learner's language ("German", "독일어"). */
export function languageName(code: string, fallback = code): string {
  const key = `lang.${code}`
  return key in en ? t(key as MessageKey) : fallback
}

/** A speech model by its id, named in the learner's language. */
export function modelName(id: string, fallback: string): string {
  const key = `models.${id}`
  return key in en ? t(key as MessageKey) : fallback
}

/** A voice's label ("Emma · British · female"): its name as it is, and what is said of it in the
 * learner's language. */
export function voiceLabel(label: string): string {
  return label.split(' · ').map(tc).join(' · ')
}
