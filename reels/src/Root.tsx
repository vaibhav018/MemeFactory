import React from 'react';
import {Composition, getInputProps} from 'remotion';
import {Reel} from './Reel';
import {Curated} from './Curated';
import {W, H, FPS} from './theme';
import {
  defaultReel,
  defaultCurated,
  type Reel as ReelData,
  type Curated as CuratedData,
} from './types';

/**
 * Two formats, rendered the same way:
 *
 *   npx remotion render Reel    out/x.mp4 --props=data/<id>.reel.json
 *   npx remotion render Curated out/x.mp4 --props=data/<id>.curated.json
 *
 * Reel    — our own voiceover, portrait and beat cards.
 * Curated — a tweet-style header over someone else's clip. Cheaper to make and,
 *           on the competitor sample, the better performer.
 *
 * Duration comes from the JSON in both cases, so a composition is exactly as
 * long as its audio or its source video.
 */
const TAIL_SECONDS = 1.2;

export const RemotionRoot: React.FC = () => {
  const input = getInputProps() as Partial<ReelData & CuratedData>;

  const reel: ReelData = {...defaultReel, ...(input as Partial<ReelData>)};
  const curated: CuratedData = {...defaultCurated, ...(input as Partial<CuratedData>)};

  const frames = (seconds: number, tail: number) =>
    Math.max(1, Math.round((seconds + tail) * FPS));

  return (
    <>
      <Composition
        id="Reel"
        component={Reel}
        durationInFrames={frames(reel.durationInSeconds || defaultReel.durationInSeconds, TAIL_SECONDS)}
        fps={FPS}
        width={W}
        height={H}
        defaultProps={reel}
      />
      {/* No tail: the clip ending is the ending. Dead frames read as a mistake. */}
      <Composition
        id="Curated"
        component={Curated}
        durationInFrames={frames(curated.durationInSeconds || defaultCurated.durationInSeconds, 0)}
        fps={FPS}
        width={W}
        height={H}
        defaultProps={curated}
      />
    </>
  );
};
