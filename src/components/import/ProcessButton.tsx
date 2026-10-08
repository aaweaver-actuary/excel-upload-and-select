import { BaseButton } from '../base/BaseButton';

export function ProcessButton({ disabled, onClick }: { disabled: boolean; onClick: () => void }) {
  return <BaseButton variant="primary" disabled={disabled} onClick={onClick}>Process data</BaseButton>;
}
