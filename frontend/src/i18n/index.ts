import { getActivePinia } from 'pinia'
import { useSettingsStore } from '../stores/settings'
import contentBn from './content.bn.json'
import contentDe from './content.de.json'
import contentEs from './content.es.json'
import contentFr from './content.fr.json'
import contentHi from './content.hi.json'
import contentId from './content.id.json'
import contentIt from './content.it.json'
import contentJa from './content.ja.json'
import contentKo from './content.ko.json'
import contentPl from './content.pl.json'
import contentPt from './content.pt.json'
import contentRu from './content.ru.json'
import contentTh from './content.th.json'
import contentTr from './content.tr.json'
import contentUk from './content.uk.json'
import contentVi from './content.vi.json'
import contentZhHans from './content.zh-Hans.json'
import contentZhHant from './content.zh-Hant.json'
import en from './en'
import bn from './bn'
import de from './de'
import es from './es'
import fr from './fr'
import hi from './hi'
import id from './id'
import it from './it'
import ja from './ja'
import ko from './ko'
import pl from './pl'
import pt from './pt'
import ru from './ru'
import th from './th'
import tr from './tr'
import uk from './uk'
import vi from './vi'
import zhHans from './zh-Hans'
import zhHant from './zh-Hant'

/** A text of the pages, by its key in `en.ts`. */
export type MessageKey = keyof typeof en

// The languages the pages are written in, by the name the learner's language is saved under
// (see LANGUAGES in the settings store): every one of them. A language without a file here would
// be shown the English pages. To add one, write a file like `ko.ts` (and `content.ko.json`) and
// list it here.
const MESSAGES: Record<string, Record<MessageKey, string>> = {
  English: en,
  Korean: ko,
  Japanese: ja,
  'Simplified Chinese': zhHans,
  'Traditional Chinese': zhHant,
  Spanish: es,
  French: fr,
  German: de,
  Italian: it,
  Portuguese: pt,
  Polish: pl,
  Russian: ru,
  Ukrainian: uk,
  Turkish: tr,
  Vietnamese: vi,
  Thai: th,
  Indonesian: id,
  Hindi: hi,
  Bengali: bn,
}
// The built-in topics, categories, and pattern notes, which the backend keeps in English, by
// their English text.
const CONTENT: Record<string, Record<string, string>> = {
  Korean: contentKo,
  Japanese: contentJa,
  'Simplified Chinese': contentZhHans,
  'Traditional Chinese': contentZhHant,
  Spanish: contentEs,
  French: contentFr,
  German: contentDe,
  Italian: contentIt,
  Portuguese: contentPt,
  Polish: contentPl,
  Russian: contentRu,
  Ukrainian: contentUk,
  Turkish: contentTr,
  Vietnamese: contentVi,
  Thai: contentTh,
  Indonesian: contentId,
  Hindi: contentHi,
  Bengali: contentBn,
}

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
