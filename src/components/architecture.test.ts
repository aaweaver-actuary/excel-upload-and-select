import { readFileSync, readdirSync } from "node:fs";
import { basename, dirname, join, relative } from "node:path";
import ts from "typescript";
import { expect, it } from "vitest";

const sourceRoot = join(process.cwd(), "src");
const baseRoot = join(sourceRoot, "components/base");

function componentFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory()
      ? componentFiles(path)
      : entry.name.endsWith(".tsx") && !entry.name.endsWith(".test.tsx")
        ? [path]
        : [];
  });
}

function parse(path: string) {
  return ts.createSourceFile(
    path,
    readFileSync(path, "utf8"),
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TSX,
  );
}

function nativeTags(source: ts.SourceFile) {
  const tags: string[] = [];
  function visit(node: ts.Node) {
    if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
      const name = node.tagName.getText(source);
      if (/^[a-z]/.test(name)) tags.push(name);
    }
    ts.forEachChild(node, visit);
  }
  visit(source);
  return tags;
}

it("keeps native HTML in exactly one base file per supported element type", () => {
  const baseTags: string[] = [];
  for (const path of componentFiles(sourceRoot)) {
    const tags = nativeTags(parse(path));
    if (dirname(path) === baseRoot) {
      expect(tags, relative(sourceRoot, path)).toHaveLength(1);
      baseTags.push(...tags);
    } else {
      expect(tags, relative(sourceRoot, path)).toEqual([]);
    }
  }
  expect(baseTags.sort()).toEqual(
    [
      "a",
      "button",
      "caption",
      "code",
      "dd",
      "details",
      "div",
      "dl",
      "dt",
      "h1",
      "h2",
      "h3",
      "input",
      "label",
      "li",
      "main",
      "nav",
      "option",
      "p",
      "section",
      "select",
      "span",
      "strong",
      "summary",
      "table",
      "tbody",
      "td",
      "th",
      "thead",
      "tr",
      "ul",
    ].sort(),
  );
});

it("gives each component its own named script and keeps its stylesheet adjacent", () => {
  for (const path of componentFiles(join(sourceRoot, "components"))) {
    const source = parse(path);
    const exports = source.statements
      .filter(ts.isFunctionDeclaration)
      .filter((node) =>
        node.modifiers?.some(
          (modifier) => modifier.kind === ts.SyntaxKind.ExportKeyword,
        ),
      );
    expect(
      exports.map((node) => node.name?.text),
      relative(sourceRoot, path),
    ).toEqual([basename(path, ".tsx")]);
    for (const node of source.statements.filter(ts.isImportDeclaration)) {
      const specifier = (node.moduleSpecifier as ts.StringLiteral).text;
      if (specifier.endsWith(".module.css")) {
        expect(specifier).toBe(`./${basename(path, ".tsx")}.module.css`);
        expect(
          readFileSync(join(dirname(path), specifier), "utf8").length,
        ).toBeGreaterThan(0);
      }
    }
  }
});
