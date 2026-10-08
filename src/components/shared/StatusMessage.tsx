import { BaseParagraph } from '../base/BaseParagraph';
import type { BaseParagraphProps } from '../base/BaseParagraph';

export function StatusMessage(props: BaseParagraphProps) {
  return <BaseParagraph role="status" {...props} />;
}
