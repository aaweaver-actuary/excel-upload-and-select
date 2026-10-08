import type { BatchJob } from "../../types";
import { Disclosure } from "../shared/Disclosure";
import { DefinitionList } from "../shared/DefinitionList";
import { readable } from "./resultFormatting";

export function ProcessingVersions({
  versions,
}: {
  versions: NonNullable<BatchJob["versions"]>;
}) {
  const items = [
    ...Object.entries(versions)
      .filter(([key]) => key !== "scorers")
      .map(([key, value]) => ({
        key: `version-${key}`,
        label: readable(key),
        value: String(value),
      })),
    ...Object.entries(versions.scorers).map(([name, version]) => ({
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
