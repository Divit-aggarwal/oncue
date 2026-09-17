import {Layout, type Node} from '@revideo/2d';
import {all} from '@revideo/core';
import {safeArea, space} from '../lib/theme';
import {draw, fadeIn, place} from '../motions';
import {Arrow} from './Arrow';
import {ConceptBox} from './ConceptBox';

// A vertical chain of boxes joined by arrows, centred in the safe area.
// `reveal(n)` shows the next n steps (arrow, then box), so a chain can be revealed across several words.
export function FlowStep({labels, width = 520}: {labels: string[]; width?: number}) {
  const boxes = labels.map(label => <ConceptBox label={label} width={width} opacity={0} />);
  const arrows = boxes.slice(1).map((box, i) => <Arrow from={boxes[i]} to={box} layout={false} />);
  const node = (
    <Layout layout direction="column" alignItems="center" gap={space.lg} y={safeArea.centerY}>
      {boxes}
      {arrows}
    </Layout>
  ) as Layout;

  let shown = 0;
  function* reveal(n = 1) {
    for (const end = Math.min(shown + n, boxes.length); shown < end; shown++) {
      if (shown === 0) place(node);
      // The arrow draws while its box fades in, so each step takes one fast duration.
      yield* all(fadeIn(boxes[shown]), ...(shown > 0 ? [draw(arrows[shown - 1])] : []));
    }
  }
  return {node: node as Node, boxes, reveal};
}
