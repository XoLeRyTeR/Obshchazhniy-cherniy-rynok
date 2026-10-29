import { strict as assert } from "node:assert";
import { test } from "node:test";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("../src/", import.meta.url));
const layers = ["app", "pages", "features", "entities", "shared"];

function files(folder: string): string[] {
  return readdirSync(folder, { withFileTypes: true }).flatMap((entry) => {
    const path = join(folder, entry.name);
    return entry.isDirectory() ? files(path) : /\.tsx?$/.test(path) ? [path] : [];
  });
}

function resolveImport(file: string, specifier: string) {
  const path = resolve(dirname(file), specifier);
  return [path, path + ".ts", path + ".tsx", join(path, "index.ts")]
    .find((candidate) => /\.tsx?$/.test(candidate) && existsSync(candidate));
}

test("FSD: слои импортируют только нижние слои и публичные API слайсов", () => {
  // Проверяем реальные import/export, включая типы: без обратных зависимостей и скрытых cross-import.
  const errors: string[] = [];
  for (const file of files(root)) {
    const from = relative(root, file).split(sep);
    assert.ok(layers.includes(from[0]), `Файл вне слоёв FSD: ${file}`);
    const ast = ts.createSourceFile(file, readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true);
    for (const node of ast.statements) {
      if (!ts.isImportDeclaration(node) && !ts.isExportDeclaration(node)) continue;
      const specifier = node.moduleSpecifier;
      if (!specifier || !ts.isStringLiteral(specifier) || !specifier.text.startsWith(".")) continue;
      const target = resolveImport(file, specifier.text);
      if (!target) { errors.push(`${file}: не найден ${specifier.text}`); continue; }
      const to = relative(root, target).split(sep);
      const sameLayer = from[0] === to[0];
      const sameSlice = sameLayer && from[1] === to[1];
      // @x явно описывает связь сущностей: тип статуса объявления или подпись общежития.
      const crossApi = from[0] === "entities" && to[0] === "entities"
        && to[2] === "@x" && to[3] === from[1] + ".ts";
      if (layers.indexOf(to[0]) < layers.indexOf(from[0]))
        errors.push(`${file}: импорт верхнего слоя ${specifier.text}`);
      if (sameLayer && !sameSlice && !["app", "shared"].includes(from[0]) && !crossApi)
        errors.push(`${file}: соседний слайс ${specifier.text}`);
      if (["pages", "features", "entities"].includes(to[0]) && !sameSlice && !crossApi
          && (to.length !== 3 || to[2] !== "index.ts"))
        errors.push(`${file}: обход публичного index.ts ${specifier.text}`);
    }
  }
  assert.deepEqual(errors, []);
});

test("стили компонентов вынесены из TSX в соседние файлы", () => {
  // Проверяем обычные props, массивы, условные стили и вложенные настройки навигации.
  const errors: string[] = [];
  const styleProps = new Set([
    "style", "contentContainerStyle", "contentStyle", "tabBarStyle",
    "tabBarLabelStyle", "sceneStyle", "tabBarBadgeStyle",
  ]);
  for (const file of files(root).filter((path) => path.endsWith(".tsx"))) {
    const ast = ts.createSourceFile(file, readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true);
    function checkStyle(node: ts.Node) {
      if (ts.isObjectLiteralExpression(node)) {
        const line = ast.getLineAndCharacterOfPosition(node.getStart(ast)).line + 1;
        errors.push(`${file}:${line}: inline-стиль`);
      } else ts.forEachChild(node, checkStyle);
    }
    function walk(node: ts.Node) {
      if (ts.isJsxAttribute(node) && styleProps.has(node.name.getText(ast))
          && node.initializer && ts.isJsxExpression(node.initializer) && node.initializer.expression)
        checkStyle(node.initializer.expression);
      else if (ts.isPropertyAssignment(node) && styleProps.has(node.name.getText(ast)))
        checkStyle(node.initializer);
      else if (ts.isCallExpression(node) && node.expression.getText(ast) === "StyleSheet.create")
        errors.push(`${file}: StyleSheet.create внутри компонента`);
      else ts.forEachChild(node, walk);
    }
    walk(ast);
  }
  assert.deepEqual(errors, []);
});
