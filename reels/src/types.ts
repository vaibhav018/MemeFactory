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

/**
 * `at` is seconds. `cue` is optional: a phrase from the VO marking where this
 * card belongs. scripts/snap_beats.py rewrites `at` to the moment that phrase
 * is actually spoken, which is the only reliable way to place cards — beats
 * are hand-timed against a guess at the VO length, and the generated audio
 * never matches the guess. The first real reel drifted 2.4s without it.
 */
type BeatBase = {at: number; cue?: string};

export type Beat =
  | (BeatBase & {type: 'hook'; text: string; sub?: string})
  | (BeatBase & {type: 'point'; num: string; title: string; body?: string})
  | (BeatBase & {type: 'stat'; stat: string; unit?: string; caption: string})
  | (BeatBase & {type: 'cta'; text: string; sub?: string});

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

/**
 * The curated-clip format: a tweet-style header over someone else's video.
 * No voiceover and no captions of our own — the source clip carries itself.
 */
export type Curated = {
  id: string;
  displayName?: string;
  handle?: string;
  verified?: boolean;
  /** One or two lines of take. `**bold**` marks the phrases that carry it. */
  commentary: string;
  /** Public path under reels/public, e.g. "video/redalert.mp4". */
  videoSrc: string;
  /**
   * Width/height of the source clip. The video box is sized from this so a
   * 16:9 clip fills edge to edge at its natural shape, which is what
   * @evolving.ai's layout actually does. 16/9 covers most found footage;
   * use 1 for square, 9/16 for a vertical source.
   */
  sourceAspect?: number;
  /**
   * Crop a band out of the source, as fractions of its height. Found footage
   * is often already someone's finished vertical post with their own header
   * baked in; this lifts out just the underlying clip. Done in the composition
   * rather than by re-encoding, so there is no generation loss.
   */
  sourceCrop?: {top: number; height: number};
  /** Trim the source. Seconds from its start. */
  startFrom?: number;
  durationInSeconds: number;
  /** Always fill this in. Someone made the clip. */
  credit?: {name: string; note?: string};
  /** Caption for the post; the credit belongs in here too. */
  caption?: string;
};

export const defaultCurated: Curated = {
  id: 'demo-curated',
  displayName: 'Profit Prompts',
  handle: '@profit_prompts_',
  verified: true,
  commentary:
    'Someone rebuilt a **$200/month workflow** with free tools and the output ' +
    'is genuinely **indistinguishable**',
  videoSrc: '',
  durationInSeconds: 15,
  credit: {name: '@creator'},
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
