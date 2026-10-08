# Editing the UI

Each component has one named `.tsx` script. Styled components have an adjacent
`.module.css` file. Open the component's script to edit what it renders, or its
stylesheet to edit how it looks.

## Where to start

| What you want to change | Where to edit |
| --- | --- |
| Page section order | `src/App.tsx` and `import/ImportScreen.tsx` |
| Page title | `layout/PageHeader.tsx` |
| Shared page-heading appearance (`h1`) | `base/BaseHeader.module.css` |
| Shared section-heading appearance (`h2`) | `base/BaseSubheader.module.css` |
| Detail headings (`h3`) | `base/BaseDetailHeader.tsx`; add an adjacent stylesheet when needed |
| Shared button appearance | `base/BaseButton.module.css` |
| Import instructions and limits wording | `import/ImportInstructions.tsx` |
| File picker | `import/FilePicker.tsx` and its stylesheet |
| Filename and worksheet selector | `import/WorksheetPicker.tsx` and its stylesheet |
| Workbook preview | `import/ColumnPreview.tsx` and `import/WorkbookPreviewTable.tsx` |
| Mapping layout and instructions | `import/MappingSection.tsx` and its stylesheet |
| Each mapping field and approval controls | `import/MappingField.tsx` and its stylesheet |
| Process button wording | `import/ProcessButton.tsx` |
| Job status and counts | `jobs/JobSummary.tsx` |
| Results filter and pagination | `jobs/ResultsFilter.tsx`, `jobs/ResultsPagination.tsx`, and their stylesheets |
| Result columns and cells | `jobs/ResultsTable.tsx` and `jobs/ResultTableRow.tsx` |
| Expandable row details | `jobs/RowDetails.tsx`, `jobs/NormalizedInputs.tsx`, `jobs/NaicsDetails.tsx`, and `jobs/ScoreDetails.tsx` |
| Issue explanations | `jobs/IssueList.tsx` |
| Shared colors, spacing, and sizes | `src/theme.css` |

Paths without `src/` in this table are relative to this directory.
Schema field labels and import limits come from the backend; changing the UI
wording does not change the allowed file size or row count.

## How the folders fit together

- `base`: one component per supported HTML element type. These are the only
  production scripts that construct native HTML directly.
- `layout`: the app shell, panel, page heading, and spaced sections.
- `shared`: reusable labeled controls, messages, disclosures, definition lists,
  table containers, and hint text.
- `import`: named components for the upload and mapping workflow.
- `jobs`: named components for progress and processing results.

The base header names have fixed semantic levels: `BaseHeader` renders `h1`,
`BaseSubheader` renders `h2`, and `BaseDetailHeader` renders `h3`. Changing their
font size does not change their heading level.

## Edit wording or appearance

Feature wording lives in its named component. For example, edit the label in
`FilePicker.tsx` to rename the upload control. Keep its surrounding `BaseLabel`
so the input remains accessible.

To change one component's styling, edit its adjacent stylesheet:

```css
/* FilePicker.module.css */
.label {
  gap: var(--space-12);
}
```

To change every base button, edit `BaseButton.module.css`. To change the primary
color wherever it is used, edit the shared variable in `src/theme.css`:

```css
:root {
  --color-primary: #2563eb;
}
```

Plain elements need no empty stylesheet. If you style one later, add
`ComponentName.module.css` beside its script and import it there. Global
`src/styles.css` is reserved for document defaults and resets.

## Create a specialized component

Use composition and normal props. The base components accept the corresponding
native React HTML props, including children, attributes, events, accessibility
attributes, and caller classes. Buttons also accept `variant="primary"`.

```tsx
// Save as components/import/ReviewButton.tsx.
import { BaseButton } from '../base/BaseButton';
import type { BaseButtonProps } from '../base/BaseButton';

export function ReviewButton(props: BaseButtonProps) {
  return <BaseButton variant="primary" {...props}>Review mappings</BaseButton>;
}
```

Then use the named component in its section:

```tsx
<ReviewButton disabled={busy} onClick={onReview} />
```

This keeps a specialized button easy to find and lets shared changes flow from
the base. Repeated component instances use the same script.

## Reorder sections and connect behavior

`App.tsx` arranges the page shell, heading, connection feedback, and import
screen. `ImportScreen.tsx` arranges the import instructions, file picker,
worksheet picker, feedback, preview, mappings, and job progress.

Move a component's JSX block to reorder it, keeping its existing props and
conditions attached. For example, move `ColumnPreview` below `MappingSection`
to place the preview after the mapping controls.

Workflow state and requests live in `src/hooks`:

| Hook | Responsibility |
| --- | --- |
| `useSchema` | Column definitions and connection retry |
| `useImport` | Workbook reading, worksheet changes, mappings, approval, and job creation |
| `useJobProgress` | Two-second polling, terminal states, and status retry |
| `useJobResults` | Result fetching, filters, pagination, and retry |
| `useLatestTask` | Ignore stale asynchronous results and errors |

Components receive data and callbacks from these hooks. ExcelJS workbook
objects stay inside the import hook; the worksheet picker receives only a
filename, choices, selected ID, and selection callback.

## Check your changes

Run `npm run typecheck`, `npm run test:coverage`, and `npm run build`.
Tests enforce one component per script and one base file per HTML element type,
and cover native props and the complete import/results workflow.

Check the affected screen at a desktop width and a narrow width. Existing
behavior includes horizontal scrolling inside tables, panel padding changing at
640px, differently sized mapping and worksheet selectors, boxed import errors,
and plain job/results errors.
