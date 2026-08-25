import React from 'react';
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from 'remotion';
import {theme, font, SAFE} from './theme';
import {Fonts} from './Fonts';
import {Captions} from './components/Captions';
import {Beats} from './components/Beats';
import type {Reel as ReelData} from './types';

/**
 * The reel.
 *
 * Layer order, back to front: ground -> optional generated b-roll -> beat card
 * -> captions -> brand chrome. No presenter: this pipeline never renders a
 * photograph of a person. The b-roll is deliberately optional — LTX-2.5 output
 * is garnish, and a missing clip must never stop a scheduled post.
 */
export const Reel: React.FC<ReelData> = ({
  audioSrc,
  captions,
  beats,
  brollSrc,
  handle = '@profit_prompts_',
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  // Slow ambient drift on the ground so flat black never sits perfectly still.
  const shift = interpolate(frame, [0, durationInFrames], [0, 40]);

  return (
    <AbsoluteFill style={{background: theme.ink}}>
      <Fonts />

      {/* halftone ground, matching the carousel's fallback panel */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 1.5px 1.5px, ${theme.accent}22 1.1px, transparent 1.2px)`,
          backgroundSize: '10px 10px',
          transform: `translateY(${shift}px)`,
          opacity: 0.5,
        }}
      />

      {brollSrc ? (
        <AbsoluteFill style={{opacity: 0.32}}>
          <OffthreadVideo
            src={staticFile(brollSrc)}
            muted
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        </AbsoluteFill>
      ) : null}

      {/* No presenter. This pipeline never renders a photograph of a person. */}
      <Beats beats={beats} />
      <Captions captions={captions} />

      {/* brand rail + handle */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: 14,
          background: theme.accent,
          zIndex: 6,
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: 96,
          left: SAFE.side,
          fontFamily: font.mono,
          fontSize: 28,
          fontWeight: 700,
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: theme.paper,
          zIndex: 6,
        }}
      >
        Profit <span style={{background: theme.accent, color: theme.ink, padding: '2px 10px'}}>Prompts</span>
      </div>
      <div
        style={{
          position: 'absolute',
          bottom: 150,
          left: 0,
          right: 0,
          textAlign: 'center',
          fontFamily: font.mono,
          fontSize: 26,
          letterSpacing: '0.14em',
          color: theme.muted,
          zIndex: 6,
        }}
      >
        {handle}
      </div>

      {audioSrc ? <Audio src={staticFile(audioSrc)} /> : null}
    </AbsoluteFill>
  );
};
