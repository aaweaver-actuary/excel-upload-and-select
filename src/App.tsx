import { useSchema } from "./hooks/useSchema";
import { AppShell } from "./components/layout/AppShell";
import { Panel } from "./components/layout/Panel";
import { PageHeader } from "./components/layout/PageHeader";
import { SchemaFeedback } from "./components/shared/SchemaFeedback";
import { ImportScreen } from "./components/import/ImportScreen";

export default function App() {
  const { schema, busy, error, loadSchema } = useSchema();
  return (
    <AppShell>
      <Panel>
        <PageHeader />
        <SchemaFeedback busy={busy} error={error} onRetry={loadSchema} />
        {schema !== null && <ImportScreen schema={schema} />}
      </Panel>
    </AppShell>
  );
}
