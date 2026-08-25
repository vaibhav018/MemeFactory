import React from 'react';
import {Img, staticFile, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {theme, PORTRAIT_W} from '../theme';

/**
 * The presenter: a background-free PNG of the operator, bottom-anchored,
 * drifting slowly upward with a faint scale so a still image reads as alive.
 *
 * The cutout is produced once by scripts/cutout_portrait.py and committed,
 * rather than removed at render time — it is a static asset, and running a
 * segmentation model on every CI render would be minutes of pure waste.
 */
export const Portrait: React.FC<{src?: string}> = ({src = 'portrait.png'}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const drift = interpolate(frame, [0, durationInFrames], [0, -46], {
    extrapolateRight: 'clamp',
  });
  const scale = interpolate(frame, [0, durationInFrames], [1.0, 1.06], {
    extrapolateRight: 'clamp',
  });

  return (
    <div style={{position: 'absolute', inset: 0, zIndex: 2}}>
      {/* Glow behind the subject separates them from the flat ground. */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          bottom: 0,
          width: 1400,
          height: 1400,
          transform: 'translateX(-50%)',
          background: `radial-gradient(circle at 50% 62%, ${theme.accent}22, transparent 62%)`,
        }}
      />
      <Img
        src={staticFile(src)}
        style={{
          position: 'absolute',
          bottom: drift,
          left: '50%',
          width: PORTRAIT_W,
          transform: `translateX(-50%) scale(${scale})`,
          transformOrigin: 'bottom center',
          filter: 'drop-shadow(0 0 60px rgba(0,0,0,.6))',
        }}
      />
      {/* Floor fade so the cutout does not end in a hard horizontal edge. */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: 620,
          background: `linear-gradient(180deg, transparent, ${theme.ink} 72%)`,
        }}
      />
    </div>
  );
};
