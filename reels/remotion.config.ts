import {Config} from '@remotion/cli/config';

/**
 * Tuned for a 2-core GitHub Actions runner, which is the real constraint —
 * a 45s reel at 30fps is 1,350 frames and the publish job has a 25 minute
 * ceiling. If renders start crowding that, drop FPS to 24 in theme.ts before
 * touching quality: Instagram re-encodes on upload anyway.
 */
Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(90);
Config.setCodec('h264');
Config.setCrf(23);
Config.setConcurrency(2);
Config.setChromiumOpenGlRenderer('angle');
Config.setEntryPoint('./src/index.ts');
