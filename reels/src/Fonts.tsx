import React from 'react';
import {staticFile, continueRender, delayRender} from 'remotion';

/**
 * Bundled OFL fonts, same three faces the carousel template uses. They are
 * loaded from public/ rather than a CDN so local renders and CI renders are
 * byte-identical — the same reason templates/slide.html embeds them.
 *
 * Rendering is held until the faces are ready; without this the first frames
 * measure against fallback metrics and the type jumps.
 */
export const Fonts: React.FC = () => {
  const [handle] = React.useState(() => delayRender('loading fonts'));

  React.useEffect(() => {
    const faces = [
      new FontFace('Anton', `url(${staticFile('fonts/Anton-Regular.ttf')})`),
      new FontFace('InterVar', `url(${staticFile('fonts/Inter-Variable.ttf')})`, {
        weight: '100 900',
      }),
      new FontFace('MonoVar', `url(${staticFile('fonts/JetBrainsMono-Variable.ttf')})`, {
        weight: '100 800',
      }),
    ];
    // FontFaceSet.add exists at runtime in Chromium but is missing from this
    // TS DOM lib, so the set is narrowed rather than casting the whole call.
    const fontSet = document.fonts as FontFaceSet & {add(f: FontFace): void};

    Promise.all(
      faces.map((f) => f.load().then((loaded) => fontSet.add(loaded)))
    )
      .then(() => continueRender(handle))
      .catch(() => continueRender(handle));
  }, [handle]);

  return null;
};
