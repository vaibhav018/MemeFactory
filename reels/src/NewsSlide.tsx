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
import {theme, font} from './theme';
import {Fonts} from './Fonts';
import type {NewsSlide as NewsSlideData} from './types';

/**
 * One item of a roundup carousel, as a video slide.
 *
 * Copied structurally from @evolving.ai's weekly roundup, whose 20-slide post
 * runs NINE video children. Measured off their 720x900 frames and scaled to
 * 1080x1350:
 *
 *   brand lockup   top right, small          ~2-6% down
 *   headline       dash-led, bold            ~9-11%
 *   body           2-4 lines, muted          ~15-26%
 *   footage        rounded window, full bleed to the margins, ~28-98%
 *
 * The point is that the footage is of the thing being described. An animated
 * version of our own text is not the same format and does not do the same job:
 * people stop for the clip, then read the headline to find out what it is.
 */
const PAD = 60;
const RADIUS = 28;

export const NewsSlide: React.FC<NewsSlideData> = ({
  headline,
  body,
  videoSrc,
  sourceCrop,
  startFrom,
  sourceAspect = 16 / 9,
  handle = '@profit_prompts_',
  displayName = 'Profit Prompts',
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();

  const enter = interpolate(frame, [0, fps * 0.35], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const winW = width - PAD * 2;
  const areaTop = Math.round(height * 0.28);
  const areaH = height - areaTop - PAD;

  // The window takes the FOOTAGE's shape, not a fixed box. Forcing a 2:1 band
  // into a near-square window with objectFit:cover zooms it four times and the
  // result is unreadable mush — which is exactly what the first render did.
  const shownAspect = sourceCrop ? sourceAspect / sourceCrop.height : sourceAspect;
  const winH = Math.min(areaH, Math.round(winW / shownAspect));
  const winTop = areaTop + Math.round((areaH - winH) / 2);

  // Crop by rendering at full height inside the window and offsetting, rather
  // than re-encoding the source.
  const fullH = sourceCrop ? Math.round(winW / sourceAspect) : winH;
  const offsetY = sourceCrop ? Math.round(fullH * sourceCrop.top) : 0;

  return (
    <AbsoluteFill style={{background: theme.ink, color: theme.paper}}>
      <Fonts />

      {/* brand lockup, top right — small enough to be a signature, not a header */}
      <div
        style={{
          position: 'absolute',
          top: 34,
          right: PAD,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          opacity: 0.96,
        }}
      >
        <Img src={staticFile('logo.png')} style={{width: 52, height: 52, borderRadius: '50%'}} />
        <div style={{lineHeight: 1.15}}>
          <div style={{fontFamily: font.body, fontSize: 23, fontWeight: 800}}>
            {displayName}
          </div>
          <div style={{fontFamily: font.body, fontSize: 21, color: '#8E949B'}}>
            {handle}
          </div>
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          top: Math.round(height * 0.088),
          left: PAD,
          right: PAD,
          opacity: enter,
          transform: `translateY(${interpolate(enter, [0, 1], [14, 0])}px)`,
        }}
      >
        <div
          style={{
            fontFamily: font.body,
            fontSize: 38,
            fontWeight: 800,
            letterSpacing: '-0.015em',
            lineHeight: 1.2,
            textWrap: 'balance',
          }}
        >
          – {headline}
        </div>
        <div
          style={{
            fontFamily: font.body,
            fontSize: 31,
            fontWeight: 400,
            lineHeight: 1.34,
            color: '#D6DADE',
            marginTop: 20,
          }}
        >
          {body}
        </div>
      </div>

      {/* the footage itself */}
      <div
        style={{
          position: 'absolute',
          top: winTop,
          left: PAD,
          width: winW,
          height: winH,
          borderRadius: RADIUS,
          overflow: 'hidden',
          background: '#000',
        }}
      >
        <OffthreadVideo
          src={staticFile(videoSrc)}
          startFrom={startFrom ? Math.round(startFrom * fps) : undefined}
          style={
            sourceCrop
              ? {position: 'absolute', top: -offsetY, left: 0, width: winW, height: fullH,
                 objectFit: 'cover'}
              : {width: '100%', height: '100%', objectFit: 'cover'}
          }
        />
      </div>
    </AbsoluteFill>
  );
};
