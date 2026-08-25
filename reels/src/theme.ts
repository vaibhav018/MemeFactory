/**
 * Brand tokens. These mirror templates/slide.html so the Reel and the
 * carousel read as one system — if you change a colour here, change it there.
 */
export const theme = {
  ink: '#0B0B0C',
  ink2: '#141417',
  paper: '#FFFFFF',
  accent: '#FFDE00',
  muted: '#8A8A93',
  rule: '#2A2A30',
} as const;

export const W = 1080;
export const H = 1920;
export const FPS = 30;

/**
 * Vertical budget for 1920px, worked out from an actual render:
 *   0-220     brand chrome
 *   220-900   beat card
 *   900-1450  open field (b-roll, or the ground)
 *   1450-1650 captions
 *   1650-1920 handle + Instagram's own bottom UI
 * IG overlays roughly the bottom 250px, so captions sit just above it.
 */
export const SAFE = {top: 220, bottom: 300, side: 80} as const;

export const font = {
  display: '"Anton", Impact, sans-serif',
  body: '"InterVar", system-ui, sans-serif',
  mono: '"MonoVar", ui-monospace, monospace',
} as const;
