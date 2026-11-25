/** A conversation topic: the situation the tutor plays out and the line that opens it. */
export interface Topic {
  id: number
  title: string
  situation: string
  opener: string
  /** Added by the learner, so it can be removed; the built-in topics cannot. */
  custom: boolean
  /** What a built-in topic is shown under; null for the learner's own. */
  category: string | null
  /** For a topic made from a text: the summary of it that the partner knows. Null otherwise. */
  background: string | null
}

/** How a line was spoken, measured from the audio by the local Whisper model. */
export interface Delivery {
  /** 0-100: how confidently the words were recognized, a proxy for clear pronunciation. */
  clarity: number
  unclearWords: string[]
  wordsPerMinute: number | null
}

export interface Correction {
  original: string
  improved: string
  explanation: string
}

/** One line of the conversation in progress. */
export interface Message {
  role: 'tutor' | 'learner'
  text: string
  /** Learner lines only: the tutor's fix, or null when the line was fine or not reviewed yet. */
  correction?: Correction | null
  /** Learner lines only. */
  delivery?: Delivery | null
}

/** A review of a whole conversation, written when the learner wraps it up. */
export interface Review {
  summary: string
  /** What went well, and what to work on next; a few short sentences each. */
  strengths: string[]
  focus: string[]
  /** Expressions that would have fit the conversation, with what they mean. */
  phrases: { expression: string; note: string }[]
}

/** A line of a saved conversation, as the backend returns it. */
export interface SavedMessage {
  role: 'tutor' | 'learner'
  text: string
  correction: Correction | null
  delivery: { clarity: number; unclear_words: string[]; words_per_minute: number | null } | null
}

/** A saved conversation with all its lines. */
export interface SavedConversation {
  id: number
  /** The code of the language it is held in ("en", "de"). */
  language: string
  /** Null once the topic it was held on has been removed. */
  topic_id: number | null
  title: string
  situation: string
  started_at: string
  messages: SavedMessage[]
  /** Written when the conversation is wrapped up; null until then. */
  review: Review | null
  /** The background of the topic it was held on, if that was made from a text. */
  background: string | null
}

/** A saved conversation in the history list. */
export interface ConversationSummary {
  id: number
  language: string
  topic_id: number | null
  title: string
  started_at: string
  /** How many times the learner spoke, and how many of those lines were corrected. */
  turns: number
  corrections: number
}

/**
 * A sentence to practise again: a correction made in a saved conversation, or a sentence got
 * wrong in pattern practice.
 */
/** A better way of saying something, to be learned (from a conversation or a pattern), or a
 * sentence of a video not said right after it. */
export type CorrectionKind = 'expression' | 'shadowing'

export interface SavedCorrection {
  id: string
  kind: CorrectionKind
  /** Where it comes from: one of the three is set, or none for a video since deleted. `title` is the conversation's, the pattern's, or the video's. */
  conversation_id: number | null
  pattern_id: string | null
  video: number | null
  /** For a sentence of a video not said right after it: where it stands in the video. */
  position: number | null
  title: string
  /** For a pattern mistake: the sentence that was to be said in the language practised. */
  prompt: string | null
  original: string
  improved: string
  explanation: string
  /** How many times the better sentence was said right, and when it last was. */
  practiced: number
  practiced_at: string | null
}

/** A sentence pattern and how the learner has done on it. */
export interface PatternStatus {
  id: string
  /** CEFR level, A1 to C2. */
  level: string
  pattern: string
  use: string
  example: string
  /** Finished rounds, and the score of the last one. */
  sessions: number
  last_correct: number | null
  last_total: number | null
  practiced_at: string | null
  /** Made by the learner from a sentence of a video; its level is "Yours". */
  custom: boolean
  /** Where that sentence is, while the video is still saved. */
  video: number | null
  position: number | null
}

/** One sentence of a round: shown in the learner's language, said in the language practised. */
export interface Exercise {
  prompt: string
  answer: string
}

/** One sentence of a video, with the seconds between which it is said. */
export interface VideoLine {
  start: number
  end: number
  text: string
}

/** A sentence of a saved video, and how the learner has done at shadowing it. */
export interface SavedVideoLine extends VideoLine {
  id: number
  /** How often it was shadowed, and the best score so far (0-100); null before the first try. */
  shadowed: number
  best: number | null
}

/** How one try at saying a sentence after the video went. */
export interface Shadowed {
  /** The share of the sentence's words that were heard, 0-100. */
  accuracy: number
  /** The sentence word by word, with whether each was heard. */
  words: { text: string; heard: boolean }[]
  shadowed: number
  best: number
}

/** A sentence found in the saved subtitles. */
export interface VideoHit {
  id: number
  /** The saved video it is in (our id and YouTube's), and where. */
  video: number
  video_id: string
  title: string
  position: number
  start: number
  text: string
}

/** A saved video in the list. */
export interface VideoSummary {
  id: number
  /** YouTube's own id of the video. */
  video_id: string
  title: string
  channel: string
  language: string
  /** The subtitles were made automatically by YouTube. */
  generated: boolean
  added_at: string
  sentences: number
  /** The CEFR level of what is said in it, A1 to C2; null while it has none. */
  level: string | null
}

/** A saved video with its sentences. */
/** A YouTube video like a saved one, found to study with next; not saved until it is added. */
export interface VideoSuggestion {
  video_id: string
  title: string
  channel: string
  /** Its length in seconds, when YouTube gives it. */
  duration: number | null
  /** The CEFR level its subtitles were estimated at. */
  level: string
  /** Whether its subtitles were made automatically by YouTube. */
  generated: boolean
}

export interface Video extends Omit<VideoSummary, 'sentences'> {
  lines: SavedVideoLine[]
}

/** A video's sentences in the learner's language, by the id of each sentence. */
export interface VideoTranslation {
  language: string
  lines: { line: number; text: string }[]
  /** Sentences left without a translation; asking again tries them again. */
  missing: number
}

/** A theme of the pages by its daisyUI name; empty follows the system's light or dark mode. */
export type Theme = '' | 'sos' | 'sos-night'

export type Phase = 'idle' | 'transcribing' | 'thinking' | 'reviewing'

/** A model the app downloads on first use, and how far its download is. */
export interface ModelStatus {
  id: 'speech-to-text' | 'voice'
  label: string
  state: 'missing' | 'downloading' | 'ready' | 'error'
  /** Bytes on disk so far, and the expected size when it is known. */
  downloaded: number
  total: number | null
  error: string | null
}

/** The AI model in use. The API key never reaches the page, only its last characters. */
export interface LLMSettings {
  model: string | null
  source: 'app' | 'env' | null
  key_hint: string | null
}

/** A voice the partner can speak with. */
export interface VoiceStatus {
  id: string
  label: string
  /** Bytes downloaded the first time it is chosen, and whether that has happened. */
  size: number
  downloaded: boolean
  chosen: boolean
}

/** A language the app teaches. */
export interface LearningLanguage {
  /** What it is kept under ("de"), its name in English ("German"), and its own ("Deutsch"). */
  code: string
  name: string
  native: string
  /** The browser voice that reads its lines when the app's own voice cannot. */
  locale: string
  /** A line to hear a voice with. */
  sample: string
  chosen: boolean
}
