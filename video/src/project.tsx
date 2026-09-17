/// <reference types="vite/client" />
import {makeScene2D, type View2D} from '@revideo/2d';
import {makeProject, useScene, type ThreadGenerator} from '@revideo/core';
import {colors, size} from './lib/theme';

// Every src/scenes/<slug>.tsx default-exports a generator; render.ts picks one by slug.
const scenes = import.meta.glob<(view: View2D) => ThreadGenerator>('./scenes/*.tsx', {
  eager: true,
  import: 'default',
});

const main = makeScene2D('main', function* (view) {
  const slug = useScene().variables.get('slug', '')();
  const scene = scenes[`./scenes/${slug}.tsx`];
  if (!scene) throw new Error(`no src/scenes/${slug}.tsx`);
  yield* scene(view);
});

export default makeProject({
  scenes: [main],
  variables: {slug: ''},
  settings: {
    shared: {size: {x: size.width, y: size.height}, background: colors.background},
    rendering: {fps: 30},
    preview: {fps: 30},
  },
});
