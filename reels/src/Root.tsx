import React from 'react';
import {Composition, staticFile, getInputProps} from 'remotion';
import {Reel} from './Reel';
import {W, H, FPS} from './theme';
import {defaultReel, type Reel as ReelData} from './types';

/**
 * The pipeline renders with:
 *   remotion render Reel out/reel.mp4 --props=data/<id>.reel.json
 *
 * Duration is driven by the audio length carried in the JSON, so the
 * composition is exactly as long as the voiceover plus a short tail.
 */
const TAIL_SECONDS = 1.2;

export const RemotionRoot: React.FC = () => {
  const input = getInputProps() as Partial<ReelData>;
  const data: ReelData = {...defaultReel, ...input};
  const seconds = (data.durationInSeconds || defaultReel.durationInSeconds) + TAIL_SECONDS;

  return (
    <Composition
      id="Reel"
      component={Reel}
      durationInFrames={Math.max(1, Math.round(seconds * FPS))}
      fps={FPS}
      width={W}
      height={H}
      defaultProps={data}
    />
  );
};
