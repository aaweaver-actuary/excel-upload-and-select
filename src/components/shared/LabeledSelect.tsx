import type { ReactNode } from 'react';
import { BaseLabel } from '../base/BaseLabel';
import { BaseSelect } from '../base/BaseSelect';
import type { BaseSelectProps } from '../base/BaseSelect';

export type LabeledSelectProps = BaseSelectProps & {
  label: ReactNode;
  labelClassName?: string;
};

export function LabeledSelect({ label, labelClassName, ...props }: LabeledSelectProps) {
  return <BaseLabel className={labelClassName}>{label}<BaseSelect {...props} /></BaseLabel>;
}
