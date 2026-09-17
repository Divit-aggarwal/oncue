/// <reference types="vite/client" />
import {makeScene2D, type View2D} from '@revideo/2d';
import {makeProject, useScene, type ThreadGenerator} from '@revideo/core';
import {colors, font, size} from './lib/theme';

// Every src/scenes/<slug>.tsx default-exports a generator; render.ts picks one by slug.
const scenes = import.meta.glob<(view: View2D) => ThreadGenerator>('./scenes/*.tsx', {
  eager: true,
  import: 'default',
});

const main = makeScene2D('main', function* (view) {
  const slug = useScene().variables.get('slug', '')();
  const scene = scenes[`./scenes/${slug}.tsx`];
  if (!scene) throw new Error(`no src/scenes/${slug}.tsx`);
  // Load the bundled Inter font before drawing anything; the headless browser has no system copy.
  const inter = new FontFace(font.family, 'url(/fonts/InterVariable.woff2)', {weight: '100 900'});
  document.fonts.add(inter);
  yield inter.load();
  yield* scene(view);
});

export default makeProject({
  scenes: [main],
  // Preview a reel with: VITE_SLUG=<slug> npm run preview (render passes the slug itself).
  variables: {slug: import.meta.env.VITE_SLUG ?? ''},
  settings: {
    shared: {size: {x: size.width, y: size.height}, background: colors.bg},
    rendering: {fps: 30},
    preview: {fps: 30},
  },
});
