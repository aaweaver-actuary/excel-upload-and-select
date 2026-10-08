import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import prettier from "eslint-config-prettier/flat";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig([
  globalIgnores([
    "node_modules/**",
    "dist/**",
    "coverage/**",
    ".cache/**",
    ".vite/**",
    ".venv/**",
    "backend/**",
  ]),
  {
    files: ["eslint.config.js"],
    extends: [js.configs.recommended],
    languageOptions: { globals: globals.node },
  },
  {
    files: ["src/**/*.{ts,tsx}", "vite.config.ts"],
    extends: [js.configs.recommended, tseslint.configs.recommendedTypeChecked],
    languageOptions: {
      parserOptions: {
        project: ["./tsconfig.test.json", "./tsconfig.node.json"],
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    extends: [reactHooks.configs.flat.recommended],
    languageOptions: { globals: globals.browser },
  },
  {
    files: ["src/**/*.tsx"],
    extends: [jsxA11y.flatConfigs.recommended, reactRefresh.configs.vite],
    settings: {
      "jsx-a11y": {
        components: {
          BaseButton: "button",
          BaseCode: "code",
          BaseContainer: "div",
          BaseDefinitionDescription: "dd",
          BaseDefinitionList: "dl",
          BaseDefinitionTerm: "dt",
          BaseDetails: "details",
          BaseInput: "input",
          BaseLabel: "label",
          BaseLink: "a",
          BaseList: "ul",
          BaseListItem: "li",
          BaseMain: "main",
          BaseNavigation: "nav",
          BaseOption: "option",
          BaseParagraph: "p",
          BaseSection: "section",
          BaseSelect: "select",
          BaseSpan: "span",
          BaseStrong: "strong",
          BaseSummary: "summary",
          BaseTable: "table",
          BaseTableBody: "tbody",
          BaseTableCaption: "caption",
          BaseTableCell: "td",
          BaseTableHead: "thead",
          BaseTableHeader: "th",
          BaseTableRow: "tr",
          BaseHeader: "h1",
          BaseSubheader: "h2",
          BaseDetailHeader: "h3",
        },
      },
    },
  },
  {
    files: ["vite.config.ts", "src/**/*.test.{ts,tsx}", "src/test/**/*.ts"],
    languageOptions: { globals: globals.node },
    rules: { "react-refresh/only-export-components": "off" },
  },
  {
    files: ["src/**/*.test.{ts,tsx}"],
    // Async act callbacks flush React's asynchronous work even without an await.
    rules: { "@typescript-eslint/require-await": "off" },
  },
  prettier,
]);
