/** A piece of a sentence: a word the learner can tap, or what is between two words. */
export interface Piece {
  text: string
  word: boolean
}

// A run of letters and figures, with short forms ("don't", "café’s") and words joined by a
// hyphen ("well-known") kept whole.
const WORD = /[\p{L}\p{M}\p{N}]+(?:['’-][\p{L}\p{M}\p{N}]+)*/gu
const LETTER = /\p{L}/u

/** A sentence cut into its words and what is between them; joined, the pieces are the text.
 * A number is not a word: there is nothing to look up. */
export function splitWords(text: string): Piece[] {
  const pieces: Piece[] = []
  let at = 0
  for (const match of text.matchAll(WORD)) {
    const word = LETTER.test(match[0])
    if (match.index > at) pieces.push({ text: text.slice(at, match.index), word: false })
    const last = pieces[pieces.length - 1]
    // A number is joined to what is around it, so only words stand apart.
    if (!word && last && !last.word) last.text += match[0]
    else pieces.push({ text: match[0], word })
    at = match.index + match[0].length
  }
  if (at < text.length) {
    const last = pieces[pieces.length - 1]
    if (last && !last.word) last.text += text.slice(at)
    else pieces.push({ text: text.slice(at), word: false })
  }
  return pieces
}

/** A text in pieces, with the first place a part of it stands marked. */
export interface Marked {
  text: string
  marked: boolean
}

/** The text with `part` marked where it first stands in it: as a whole word when `whole` (the
 * word tapped in its sentence, whatever its case), otherwise as it is written (the words of a
 * translation that stand for it). Unmarked when it is not there. */
export function markPart(text: string, part: string, whole = false): Marked[] {
  let start = -1
  let length = part.length
  if (whole) {
    let at = 0
    for (const piece of splitWords(text)) {
      if (piece.word && piece.text.toLowerCase() === part.toLowerCase()) {
        start = at
        length = piece.text.length
        break
      }
      at += piece.text.length
    }
  } else if (part) start = text.indexOf(part)
  if (start < 0) return [{ text, marked: false }]
  return [
    { text: text.slice(0, start), marked: false },
    { text: text.slice(start, start + length), marked: true },
    { text: text.slice(start + length), marked: false },
  ].filter((piece) => piece.text)
}
