import {Txt, type TxtProps} from '@revideo/2d';
import {colors, font, type} from '../lib/theme';

// Big bold title text.
export function Headline(props: TxtProps) {
  return (
    <Txt fill={colors.text} fontFamily={font.family} fontWeight={font.bold} fontSize={type.headline} {...props} />
  ) as Txt;
}
