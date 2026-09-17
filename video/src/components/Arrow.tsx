import {Line, type Layout, type LineProps, type Node} from '@revideo/2d';
import {colors, space, stroke} from '../lib/theme';

export interface ArrowProps extends Omit<LineProps, 'points'> {
  from: Node;
  to: Node;
}

// An arrow from one node's edge to another's, undrawn until draw(). Both nodes must share a parent.
// Joins the facing edges (stacked: bottom/top, side by side: right/left) and follows the nodes if they move.
export function Arrow({from, to, ...rest}: ArrowProps) {
  const a = from as Layout;
  const b = to as Layout;
  const points = () => {
    const d = b.position().sub(a.position());
    if (Math.abs(d.y) >= Math.abs(d.x)) {
      return d.y >= 0
        ? [a.bottom().addY(space.xs), b.top().addY(-space.xs)]
        : [a.top().addY(-space.xs), b.bottom().addY(space.xs)];
    }
    return d.x >= 0
      ? [a.right().addX(space.xs), b.left().addX(-space.xs)]
      : [a.left().addX(-space.xs), b.right().addX(space.xs)];
  };
  return (
    <Line points={points} stroke={colors.text} lineWidth={stroke} endArrow arrowSize={16} end={0} {...rest} />
  ) as Line;
}
