import {Audio, useScene2D, type Curve, type Layout, type Node} from '@revideo/2d';
import {all} from '@revideo/core';
import {duration, size} from '../lib/theme';
import {waitUntil} from '../lib/timing';

// Motions add a node to the scene if it isn't in one yet, so scenes can pass fresh JSX straight in.
export function place(...nodes: Node[]) {
  const view = useScene2D().getView();
  for (const node of nodes) if (!node.parent()) view.add(node);
}

// Fade nodes in from invisible.
export function* fadeIn(...nodes: Node[]) {
  place(...nodes);
  nodes.forEach(n => n.opacity(0));
  yield* all(...nodes.map(n => n.opacity(1, duration.fast)));
}

// Fade nodes out and remove them.
export function* fadeOut(...nodes: Node[]) {
  yield* all(...nodes.map(n => n.opacity(0, duration.fast)));
  nodes.forEach(n => n.remove());
}

// Slide a node in from off-screen to where it was placed.
export function* slideIn(node: Node, from: 'left' | 'right' | 'top' | 'bottom') {
  place(node);
  const n = node as Layout;
  const target = n.position();
  const offX = size.width / 2 + n.width() / 2; // just off-screen, so it is visible as soon as it moves
  const offY = size.height / 2 + n.height() / 2;
  const start = {left: [-offX, target.y], right: [offX, target.y], top: [target.x, -offY], bottom: [target.x, offY]}[from];
  n.position(start as [number, number]);
  yield* n.position(target, duration.normal);
}

// Draw a line or outline (Arrow, Highlight) from start to end.
export function* draw(node: Node) {
  place(node);
  yield* (node as Curve).end(1, duration.fast);
}

// Pulse a node: grow slightly and settle back.
export function* highlight(node: Node) {
  yield* node.scale(1.08, duration.normal / 2).to(1, duration.normal / 2);
}

// Clear everything except the audio so the screen is empty exactly at `wordTime` (the next beat's first word).
export function* clearScene(wordTime: number) {
  yield* waitUntil(wordTime - duration.fast);
  const nodes = useScene2D().getView().children().filter(n => !(n instanceof Audio));
  yield* fadeOut(...nodes);
}
