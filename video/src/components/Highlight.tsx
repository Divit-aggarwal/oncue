import {Rect, useScene2D, type Layout, type Node, type RectProps} from '@revideo/2d';
import {transformVectorAsPoint} from '@revideo/core';
import {colors, radius, space, stroke} from '../lib/theme';

export interface HighlightProps extends RectProps {
  target: Node;
  color?: string;
}

// An outline around an existing node, undrawn until draw(). Add it to the view (draw() does); it tracks the target.
export function Highlight({target, color = colors.accent, ...rest}: HighlightProps) {
  const t = target as Layout;
  const view = useScene2D().getView();
  return (
    <Rect
      position={() => transformVectorAsPoint(t.absolutePosition(), view.worldToLocal())}
      width={() => t.width() * t.scale.x() + 2 * space.xs}
      height={() => t.height() * t.scale.y() + 2 * space.xs}
      radius={radius + space.xs}
      stroke={color}
      lineWidth={stroke * 1.5}
      end={0}
      {...rest}
    />
  ) as Rect;
}
