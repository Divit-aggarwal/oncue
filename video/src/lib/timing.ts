import {useTime, waitFor} from '@revideo/core';

export interface Word {
  text: string;
  start: number;
  end: number;
}

export interface Timings {
  duration: number;
  words: Word[];
}

const files = import.meta.glob<Timings>('../../timings/*.json', {
  eager: true,
  import: 'default',
});

// Lowercase and strip punctuation (including Devanagari danda) so "Token," matches "token".
function tokens(text: string): string[] {
  return text
    .toLowerCase()
    .split(/\s+/)
    .map(t => t.replace(/^[\p{P}\p{S}।॥]+|[\p{P}\p{S}।॥]+$/gu, ''))
    .filter(Boolean);
}

// Create inside the scene generator: the search cursor restarts each time the scene replays.
export function loadTimings(slug: string) {
  const timings = files[`../../timings/${slug}.json`];
  if (!timings) throw new Error(`no timings/${slug}.json; run transcription first`);
  const spoken = timings.words.flatMap(w => tokens(w.text).map(t => ({t, w})));
  let cursor = 0;

  // Start time of the first 2-3 words of `phrase`, searching forward from the previous match.
  function startOf(phrase: string): number {
    const needle = tokens(phrase).slice(0, 3);
    if (needle.length === 0) throw new Error('startOf needs at least one word');
    for (let i = cursor; i + needle.length <= spoken.length; i++) {
      if (needle.every((t, k) => spoken[i + k].t === t)) {
        cursor = i + needle.length;
        return spoken[i].w.start;
      }
    }
    const heard = spoken.slice(cursor, cursor + 12).map(s => s.t).join(' ');
    throw new Error(`"${needle.join(' ')}" not found in ${slug} after word ${cursor}; next words: "${heard}"`);
  }

  return {timings, startOf};
}

// Revideo 0.11 has no waitUntil; this waits until an absolute time in seconds.
export function* waitUntil(seconds: number) {
  yield* waitFor(Math.max(0, seconds - useTime()));
}
