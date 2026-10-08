import type { ReactNode } from 'react';
import { BaseContainer } from '../base/BaseContainer';
import { BaseDefinitionList } from '../base/BaseDefinitionList';
import { BaseDefinitionTerm } from '../base/BaseDefinitionTerm';
import { BaseDefinitionDescription } from '../base/BaseDefinitionDescription';
import styles from './DefinitionList.module.css';

export interface DefinitionListItem {
  key: string;
  label: ReactNode;
  value: ReactNode;
}

export function DefinitionList({ items }: { items: DefinitionListItem[] }) {
  return <BaseDefinitionList className={styles.list}>{items.map(item =>
    <BaseContainer key={item.key} className={styles.item}>
      <BaseDefinitionTerm className={styles.term}>{item.label}</BaseDefinitionTerm>
      <BaseDefinitionDescription className={styles.value}>{item.value}</BaseDefinitionDescription>
    </BaseContainer>
  )}</BaseDefinitionList>;
}
