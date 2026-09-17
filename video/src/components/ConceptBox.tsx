import {Rect, Txt, type RectProps} from '@revideo/2d';
import {colors, font, radius, space, stroke, type} from '../lib/theme';

export interface ConceptBoxProps extends RectProps {
  label: string;
  sublabel?: string;
  variant?: 'default' | 'accent' | 'accent2';
}

// A labelled box for one concept (LLM, Retriever, notes...). Sizes to its text unless width is set.
export function ConceptBox({label, sublabel, variant = 'default', ...rest}: ConceptBoxProps) {
  const color = variant === 'default' ? colors.text : colors[variant];
  return (
    <Rect
      layout
      direction="column"
      alignItems="center"
      gap={space.xs}
      padding={[space.sm, space.md]}
      radius={radius}
      stroke={color}
      lineWidth={stroke}
      {...rest}
    >
      <Txt text={label} fill={colors.text} fontFamily={font.family} fontWeight={font.bold} fontSize={type.body} />
      {sublabel && <Txt text={sublabel} fill={colors.muted} fontFamily={font.family} fontSize={type.caption} />}
    </Rect>
  ) as Rect;
}
