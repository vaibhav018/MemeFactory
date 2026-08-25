/**
 * The reel.json contract.
 *
 * Produced by the pipeline: the writer emits `hook` and `beats`, the voice
 * step (CosyVoice on Colab, or ElevenLabs) emits `audioSrc` and `captions`
 * with per-word timings. Everything the composition needs is in here, so a
 * reel can be re-rendered deterministically from JSON alone.
 */

export type Caption = {
  /** One word. Punctuation stays attached so the line reads naturally. */
  word: string;
  /** Seconds from the start of the audio. */
  start: number;
  end: number;
};

export type Beat =
  | {at: number; type: 'hook'; text: string; sub?: string}
  | {at: number; type: 'point'; num: string; title: string; body?: string}
  | {at: number; type: 'stat'; stat: string; unit?: string; caption: string}
  | {at: number; type: 'cta'; text: string; sub?: string};

export type Reel = {
  id: string;
  /** Public path under reels/public, e.g. "audio/20260826.mp3". */
  audioSrc: string;
  /** Seconds. Drives composition length; pipeline reads it off the audio. */
  durationInSeconds: number;
  captions: Caption[];
  beats: Beat[];
  /** Optional generated b-roll (LTX). Absent is normal and fine. */
  brollSrc?: string | null;
  handle?: string;
};

export const defaultReel: Reel = {
  id: 'demo',
  audioSrc: '',
  durationInSeconds: 12,
  captions: [],
  beats: [
    {at: 0, type: 'hook', text: 'Your AI subscription is now paying twice', sub: 'And nobody told you'},
    {at: 4, type: 'point', num: '01', title: 'Check the cap', body: 'Find the number before it finds you mid-deadline.'},
    {at: 8, type: 'cta', text: 'Follow for the next one', sub: '@profit_prompts_'},
  ],
  handle: '@profit_prompts_',
};
