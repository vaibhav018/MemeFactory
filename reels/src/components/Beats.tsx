import React from 'react';
import {useCurrentFrame, useVideoConfig, interpolate, spring} from 'remotion';
import {theme, font, SAFE} from '../theme';
import type {Beat} from '../types';

/**
 * Beat cards — the visual counterpart to what the voice is saying.
 *
 * Each beat carries an `at` in seconds; the active beat is the last one whose
 * time has passed. Cards enter on a spring and hold, so the eye lands before
 * the ear catches up rather than the other way round.
 */

const useActive = (beats: Beat[]) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  let idx = -1;
  beats.forEach((b, i) => {
    if (t >= b.at) idx = i;
  });
  return {idx, t};
};

const Shell: React.FC<{startAt: number; children: React.ReactNode}> = ({
  startAt,
  children,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - startAt * fps;
  const s = spring({frame: local, fps, config: {damping: 200, mass: 0.6}});
  const y = interpolate(s, [0, 1], [44, 0]);

  return (
    <div
      style={{
        position: 'absolute',
        left: SAFE.side,
        right: SAFE.side,
        top: SAFE.top,
        opacity: s,
        transform: `translateY(${y}px)`,
        zIndex: 4,
      }}
    >
      {children}
    </div>
  );
};

export const Beats: React.FC<{beats: Beat[]}> = ({beats}) => {
  const {idx} = useActive(beats);
  if (idx < 0) return null;
  const b = beats[idx];

  if (b.type === 'hook' || b.type === 'cta') {
    return (
      <Shell startAt={b.at}>
        {b.type === 'cta' ? (
          <div
            style={{
              fontFamily: font.mono,
              fontSize: 30,
              fontWeight: 700,
              letterSpacing: '0.16em',
              textTransform: 'uppercase',
              color: theme.accent,
              marginBottom: 22,
            }}
          >
            Before you scroll
          </div>
        ) : null}
        <div
          style={{
            fontFamily: font.display,
            fontSize: 118,
            lineHeight: 0.97,
            textTransform: 'uppercase',
            color: theme.paper,
            letterSpacing: '-0.005em',
          }}
        >
          {b.text}
        </div>
        {b.sub ? (
          <div
            style={{
              fontFamily: font.body,
              fontWeight: 750,
              fontSize: 36,
              textTransform: 'uppercase',
              color: '#C9C9D2',
              marginTop: 22,
            }}
          >
            {b.sub}
          </div>
        ) : null}
      </Shell>
    );
  }

  if (b.type === 'stat') {
    return (
      <Shell startAt={b.at}>
        <div style={{display: 'flex', alignItems: 'baseline', gap: 12}}>
          <span
            style={{
              fontFamily: font.display,
              fontSize: 280,
              lineHeight: 0.84,
              color: theme.accent,
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {b.stat}
          </span>
          {b.unit ? (
            <span
              style={{
                fontFamily: font.display,
                fontSize: 92,
                color: theme.accent,
                textTransform: 'uppercase',
              }}
            >
              {b.unit}
            </span>
          ) : null}
        </div>
        <div
          style={{
            fontFamily: font.body,
            fontSize: 44,
            lineHeight: 1.3,
            color: '#E4E4E8',
            marginTop: 28,
          }}
        >
          {b.caption}
        </div>
      </Shell>
    );
  }

  // point
  return (
    <Shell startAt={b.at}>
      <div style={{display: 'flex', alignItems: 'center', gap: 24, marginBottom: 26}}>
        <div
          style={{
            fontFamily: font.display,
            fontSize: 68,
            color: theme.ink,
            background: theme.accent,
            width: 104,
            height: 104,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flex: 'none',
          }}
        >
          {b.num}
        </div>
        <div
          style={{
            fontFamily: font.display,
            fontSize: 74,
            lineHeight: 1.02,
            textTransform: 'uppercase',
            color: theme.paper,
          }}
        >
          {b.title}
        </div>
      </div>
      {b.body ? (
        <div
          style={{
            fontFamily: font.body,
            fontSize: 42,
            lineHeight: 1.34,
            color: '#E4E4E8',
          }}
        >
          {b.body}
        </div>
      ) : null}
    </Shell>
  );
};
