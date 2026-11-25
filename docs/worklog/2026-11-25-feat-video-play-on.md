---
title: "feat: play a video on without stopping, without YouTube's subtitles"
date: 2026-11-25
branch: feat/video-play-on
request-source: Claude Code session, 2026-11-25
---

## Request

Three things on the page of a video:

- YouTube draws its own subtitles over the video while it plays; they should not be shown.
- Besides listening sentence by sentence, it should be possible to simply play the video through, since the first time one wants to hear it from start to end.
- Turning the translation on makes the current place disappear from the screen; the place should be kept.

## Changes

- **YouTube's subtitles stay off.** They were hidden only while "Show the text" was off. The player now turns them off when it is ready and each time it starts to play (YouTube brings them back then), whatever the learner's own YouTube settings are. This lives in `useYouTubePlayer`; the page no longer steers it, and `setCaptions` is gone.
- **"Play on".** A new toggle next to "Repeat". With it on, playing starts at the chosen sentence (or where the video stopped) and goes on to the end; the sentence being said is marked and scrolled to, as it already was when the video was started from YouTube's own controls. Pausing and playing again goes on from where it stopped (`resumeFrom` in `video.ts`). Turning it on while a sentence plays lets the video run on; turning it off while it runs stops at the end of the sentence being said. "Repeat" is disabled while it is on, and the play button says "Play" instead of "Play the sentence". The player got `playFrom`.
- **The place is kept when the translation is shown or hidden.** Every sentence gets taller with its translation, so the one being heard was pushed down by all those above it. The page is now scrolled by as much as that sentence moved.
- **Texts**: `video.playVideo`, `video.playOn`, and `video.playOnHint` in all 19 languages of the pages (AI translations outside English and Korean, as before).
- **Docs**: the READMEs mention playing on and that YouTube's subtitles are kept off.

Considered and left out: remembering "Play on" between videos or sessions; it starts off on each video, like "Repeat".

## Verification

- `cd frontend && npm test`: 235 pass, with new tests for `playFrom` (does not stop at a sentence's end), for hiding the subtitles on ready and on each start, and for `resumeFrom`.
- `cd frontend && npm run build`: type check and build pass.
- In the running app (dev servers, a saved video): checked by hand that YouTube's subtitles do not appear, that "Play on" plays through and follows the sentence being said, and that the sentence being heard keeps its place when the translation is turned on and off.
