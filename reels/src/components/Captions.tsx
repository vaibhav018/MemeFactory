import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {theme, font, SAFE} from '../theme';
import type {Caption} from '../types';

/**
 * Word-synced captions.
 *
 * Timings come free with the TTS call, so there is no Whisper pass here.
 * Words are grouped into short lines and the line containing "now" is shown,
 * with the active word in brand yellow. Reels are watched muted more often
 * than not, so this is the primary channel, not decoration.
 */
const WORDS_PER_LINE = 3;

export const Captions: React.FC<{captions: Caption[]}> = ({captions}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  if (!captions.length) return null;

  // Group into fixed-size lines once, then find the line covering `t`.
  const lines: Caption[][] = [];
  for (let i = 0; i < captions.length; i += WORDS_PER_LINE) {
    lines.push(captions.slice(i, i + WORDS_PER_LINE));
  }

  const line = lines.find((l) => t >= l[0].start && t <= l[l.length - 1].end);
  if (!line) return null;

  return (
    <div
      style={{
        position: 'absolute',
        left: SAFE.side,
        right: SAFE.side,
        bottom: SAFE.bottom,
        textAlign: 'center',
        fontFamily: font.body,
        fontWeight: 800,
        fontSize: 64,
        lineHeight: 1.15,
        letterSpacing: '-0.02em',
        textTransform: 'uppercase',
        // Double shadow acts as a scrim: legible even if a descender from the
        // portrait's jawline ends up behind a word.
        textShadow:
          '0 4px 24px rgba(0,0,0,.95), 0 0 60px rgba(0,0,0,.85)',
        zIndex: 5,
      }}
    >
      {line.map((c, i) => {
        const active = t >= c.start && t <= c.end;
        return (
          <span
            key={i}
            style={{
              color: active ? theme.accent : theme.paper,
              marginRight: 16,
              display: 'inline-block',
            }}
          >
            {c.word}
          </span>
        );
      })}
    </div>
  );
};
