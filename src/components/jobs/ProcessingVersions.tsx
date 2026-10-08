import type { BatchJob } from "../../types";
import { Disclosure } from "../shared/Disclosure";
import { DefinitionList } from "../shared/DefinitionList";
import { readable } from "./resultFormatting";

export function ProcessingVersions({
  versions,
}: {
  versions: NonNullable<BatchJob["versions"]>;
}) {
  const { scorers, ...processingVersions } = versions;
  const items = [
    ...Object.entries(processingVersions).map(([key, value]) => ({
      key: `version-${key}`,
      label: readable(key),
      value,
    })),
    ...Object.entries(scorers).map(([name, version]) => ({
      key: `scorer-${name}`,
      label: name,
      value: version,
    })),
  ];
  return (
    <Disclosure summary="Processing versions">
      <DefinitionList items={items} />
    </Disclosure>
  );
}
