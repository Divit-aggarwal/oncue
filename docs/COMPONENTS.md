# Components and Motions

Scenes in `video/src/scenes/` should read like the storyboard. Every visual value lives in `video/src/lib/theme.ts`; every look lives in a component; every animation is a motion. Scenes never call `.opacity()` or other raw animations.

```tsx
import {ConceptBox, FlowStep, Headline, Tag, Arrow, Highlight} from '../components';
import {fadeIn, fadeOut, slideIn, draw, highlight, clearScene} from '../motions';
```

Positions are scene coordinates: `(0, 0)` is the centre of the frame, `y` grows downward. `safeArea.centerY` is the vertical centre of the area not covered by platform UI.

## Theme (`lib/theme.ts`)

| Token | Values |
|---|---|
| `colors` | `bg` #0B0B10, `text` #F5F5F7, `muted` #8E8E9A, `accent` #7F77DD, `accent2` #4FC3D9, `success` #4CC38A, `danger` #E5484D |
| `font` | `family` Inter (bundled in `public/fonts/`), `regular` 400, `bold` 700 |
| `type` | `headline` 120, `body` 56, `caption` 48 |
| `space` | `xs` 16, `sm` 32, `md` 64, `lg` 120 |
| `radius`, `stroke` | 24, 4 |
| `duration` | `fast` 0.3, `normal` 0.6, `slow` 1 |
| `safe` / `safeArea` | margins top 120, bottom 200, side 80 / the same area in scene coordinates |

## Components

All components accept the normal Revideo node props (`x`, `y`, `width`, `opacity`, `ref`, ...) in addition to their own.

### ConceptBox

A labelled box for one concept. Sizes to its text unless `width` is set.

| Prop | Type | Default |
|---|---|---|
| `label` | string | required |
| `sublabel` | string | none |
| `variant` | `'default' \| 'accent' \| 'accent2'` | `'default'` (text-coloured border) |

```tsx
yield* fadeIn(<ConceptBox label="LLM" sublabel="reads the prompt" variant="accent" y={safeArea.centerY} />);
```

### Arrow

An arrow between two nodes that share a parent. Joins facing edges (bottom→top when stacked, right→left when side by side) and follows the nodes if they move. Starts undrawn; reveal it with `draw()`.

| Prop | Type | Default |
|---|---|---|
| `from`, `to` | node | required |

```tsx
const q = <ConceptBox label="question" x={-250} />;
const llm = <ConceptBox label="LLM" x={250} />;
yield* fadeIn(q, llm);
yield* draw(<Arrow from={q} to={llm} />);
```

### FlowStep

A vertical chain of `ConceptBox`es joined by `Arrow`s, centred in the safe area. Not JSX: call it as a function. `reveal(n)` shows the next `n` steps (each step fades its box in while its arrow draws, one `fast` duration), so a chain can be revealed across several words.

| Prop | Type | Default |
|---|---|---|
| `labels` | string[] | required |
| `width` | number | 520 (all boxes the same width) |

Returns `{boxes, reveal}`.

```tsx
const flow = FlowStep({labels: ['Retriever', 'relevant docs', 'LLM', 'answer']});
yield* flow.reveal(2);                      // Retriever, arrow, relevant docs
yield* waitUntil(startOf('LLM'));
yield* flow.reveal(1);                      // arrow, LLM
```

### Tag

A small pill caption.

| Prop | Type | Default |
|---|---|---|
| `text` | string | required |
| `color` | string | `colors.muted` (border and text) |

```tsx
yield* fadeIn(<Tag text="extra context in the prompt" color={colors.accent2} y={safeArea.centerY + 180} />);
```

### Headline

Big bold title text (`type.headline`, Inter bold). Takes any `Txt` props.

```tsx
yield* fadeIn(<Headline text="RAG" y={safeArea.centerY} />);
```

### Highlight

An outline around an existing node, in scene coordinates, so it works on nodes inside a `FlowStep`. Tracks the target's position and size. Starts undrawn; reveal it with `draw()`, remove it with `fadeOut()`.

| Prop | Type | Default |
|---|---|---|
| `target` | node | required |
| `color` | string | `colors.accent` |

```tsx
const ring = <Highlight target={flow.boxes[2]} />;
yield* draw(ring);
yield* fadeOut(ring);
```

## Motions (`motions/index.ts`)

Motions add a node to the scene if it isn't in one yet, so fresh JSX can be passed straight in.

| Motion | What it does | Duration |
|---|---|---|
| `fadeIn(...nodes)` | Fade from invisible to visible. | `fast` |
| `fadeOut(...nodes)` | Fade out, then remove from the scene. | `fast` |
| `slideIn(node, from)` | Move in from just off-screen (`'left' \| 'right' \| 'top' \| 'bottom'`) to where the node was placed. | `normal` |
| `draw(node)` | Draw an `Arrow` or `Highlight` from start to end. | `fast` |
| `highlight(node)` | Pulse: grow 8% and settle back. | `normal` |
| `clearScene(wordTime)` | Wait until `wordTime - fast`, then fade out and remove everything except the audio, so the screen is empty exactly on the next beat's first word. | `fast` |

```tsx
// Beat 2: Hum bas model ko notes de rahe hain.
yield* clearScene(startOf('Hum bas model'));
yield* fadeIn(<ConceptBox label="LLM" variant="accent" x={180} y={y} />);
yield* waitUntil(startOf('notes'));
const notes = <ConceptBox label="notes" x={-180} y={y} />;
yield* slideIn(notes, 'left');
yield* highlight(notes);
```

## Adding a component

1. One file in `video/src/components/`, exported from `components/index.ts`.
2. Take every colour, size and duration from `theme.ts`.
3. Add it to this document with its props and one example.
4. Changing an existing component's look substantially means a new version (see CLAUDE.md §15).
