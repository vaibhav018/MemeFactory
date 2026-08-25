import React from 'react';
import {
  AbsoluteFill,
  Img,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from 'remotion';
import {theme, font, W, H} from './theme';
import {Fonts} from './Fonts';
import type {Curated as CuratedData} from './types';

/**
 * The curated-clip format.
 *
 * Derived from @evolving.ai, whose two best reels in the sample (99.9k and
 * 47.4k engagement) both use it: a tweet-style header, then somebody else's
 * video letterboxed below, and nothing else. No voiceover, no avatar, no
 * captions of our own. It outperformed every carousel we measured, and it
 * costs almost nothing to produce.
 *
 * The credit line is ours, not theirs — they credit in the caption only. On
 * screen it is cheap insurance and the decent thing to do with someone else's
 * footage.
 */

/** Renders **bold** spans. Key phrases carry the hook; a flat line does not. */
const RichText: React.FC<{text: string}> = ({text}) => (
  <>
    {text.split(/(\*\*[^*]+\*\*)/g).map((chunk, i) =>
      chunk.startsWith('**') && chunk.endsWith('**') ? (
        <strong key={i} style={{fontWeight: 800}}>
          {chunk.slice(2, -2)}
        </strong>
      ) : (
        <React.Fragment key={i}>{chunk}</React.Fragment>
      )
    )}
  </>
);

const Verified: React.FC = () => (
  <svg width="34" height="34" viewBox="0 0 24 24" style={{flex: 'none'}}>
    <path
      fill="#1D9BF0"
      d="M22.25 12c0-1.43-.88-2.67-2.19-3.34.46-1.39.2-2.9-.81-3.91s-2.52-1.27-3.91-.81C14.67 2.63 13.43 1.75 12 1.75s-2.67.88-3.34 2.19c-1.39-.46-2.9-.2-3.91.81S3.48 7.27 3.94 8.66C2.63 9.33 1.75 10.57 1.75 12s.88 2.67 2.19 3.34c-.46 1.39-.2 2.9.81 3.91s2.52 1.27 3.91.81c.67 1.31 1.91 2.19 3.34 2.19s2.67-.88 3.34-2.19c1.39.46 2.9.2 3.91-.81s1.27-2.52.81-3.91c1.31-.67 2.19-1.91 2.19-3.34z"
    />
    <path
      fill="#fff"
      d="M10.6 15.4L7.2 12l1.4-1.4 2 2 4.8-4.8L16.8 9.2z"
    />
  </svg>
);

/**
 * Layout measured off six @evolving.ai frames rather than guessed:
 *   header first lit row  18.6% - 21.0% of frame height
 *   video top             33.7% - 36.2%
 *   video                 full width, natural aspect, never cropped
 * Their 16:9 clips land ~31.6% tall at full width, which is what a 1080-wide
 * 16:9 video is. So there is no fixed video box — the source dictates it.
 */
const HEADER_TOP = Math.round(H * 0.195);   // 374
const GAP = 40;                             // header to clip

export const Curated: React.FC<CuratedData> = ({
  displayName = 'Profit Prompts',
  handle = '@profit_prompts_',
  commentary,
  videoSrc,
  credit,
  verified = true,
  sourceAspect = 16 / 9,
}) => {
  const videoHeight = Math.round(W / sourceAspect);
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // The header settles in the first half second. Anything longer and the
  // viewer has already decided.
  const enter = interpolate(frame, [0, fps * 0.4], [0, 1], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{background: theme.ink, color: theme.paper}}>
      <Fonts />

      {/* Header and clip flow in sequence rather than sitting at fixed offsets.
          Measuring @evolving.ai, their clip starts at 33.7% behind a one-line
          take and 36.2% behind a three-line one — the clip follows the text.
          Absolute positioning both put the video edge through the last line. */}
      <div
        style={{
          position: 'absolute',
          top: HEADER_TOP,
          left: 0,
          right: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: GAP,
        }}
      >
      <div
        style={{
          paddingLeft: 56,
          paddingRight: 56,
          opacity: enter,
          transform: `translateY(${interpolate(enter, [0, 1], [18, 0])}px)`,
        }}
      >
        <div style={{display: 'flex', alignItems: 'center', gap: 20, marginBottom: 26}}>
          <Img
            src={staticFile('avatar.png')}
            style={{
              width: 92,
              height: 92,
              borderRadius: '50%',
              flex: 'none',
              // evolving.ai rings the avatar; it separates the head from the
              // black ground, which a bare circle does not.
              border: '3px solid rgba(255,255,255,.92)',
            }}
          />
          <div style={{lineHeight: 1.12}}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                fontFamily: font.body,
                fontSize: 40,
                fontWeight: 800,
                letterSpacing: '-0.02em',
              }}
            >
              {displayName}
              {verified ? <Verified /> : null}
            </div>
            <div
              style={{
                fontFamily: font.body,
                fontSize: 36,
                fontWeight: 500,
                color: '#9BA0A6',
              }}
            >
              {handle}
            </div>
          </div>
        </div>

        <div
          style={{
            fontFamily: font.body,
            fontSize: 46,
            fontWeight: 500,
            lineHeight: 1.28,
            letterSpacing: '-0.015em',
            textWrap: 'balance',
          }}
        >
          <RichText text={commentary} />
        </div>
      </div>

        {/* Source clip: full width, natural aspect, never cropped to fill.
            Height comes from sourceAspect, so a 16:9 clip fills edge to edge
            exactly as it does on @evolving.ai. */}
        <div style={{width: W, height: videoHeight, background: '#000'}}>
          <OffthreadVideo
            src={staticFile(videoSrc)}
            style={{width: '100%', height: '100%', objectFit: 'contain'}}
          />
        </div>

        {/* Credit sits directly under the clip, where evolving.ai puts the
            source's own subtitle line. They credit in the caption only; on
            screen costs nothing and is the decent thing to do. */}
        {credit?.name ? (
          <div
            style={{
              paddingLeft: 56,
              paddingRight: 56,
              marginTop: -6,
              fontFamily: font.body,
              fontSize: 30,
              fontWeight: 500,
              color: '#7C828A',
            }}
          >
            clip by {credit.name}
            {credit.note ? ` · ${credit.note}` : ''}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
