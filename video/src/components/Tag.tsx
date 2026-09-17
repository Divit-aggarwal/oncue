import {Rect, Txt, type RectProps} from '@revideo/2d';
import {colors, font, space, stroke, type} from '../lib/theme';

export interface TagProps extends RectProps {
  text: string;
  color?: string;
}

export function Tag({text, color = colors.muted, ...rest}: TagProps) {
  return (
    <Rect layout padding={[space.xs, space.sm]} radius={999} stroke={color} lineWidth={stroke} {...rest}>
      <Txt text={text} fill={color} fontFamily={font.family} fontSize={type.caption} />
    </Rect>
  ) as Rect;
}
