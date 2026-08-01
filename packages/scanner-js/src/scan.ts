import { Project, SourceFile, SyntaxKind, Node, ExportedDeclarations } from "ts-morph";
import { resolve, relative, dirname, join } from "path";
import { existsSync } from "fs";
import {
  ExportedSymbol,
  SourceUnit,
  DependencyEdge,
  SourceGraph,
  ScanOptions,
} from "./types.js";

const DEFAULT_EXCLUDE = ["node_modules", "dist", ".git", "coverage", "__tests__"];

function getJsDoc(node: Node): string {
  const jsDocs = (node as any).getJsDocs?.();
  if (jsDocs && jsDocs.length > 0) {
    return jsDocs[0].getDescription?.()?.trim() ?? "";
  }
  return "";
}

function extractExports(sourceFile: SourceFile): ExportedSymbol[] {
  const symbols: ExportedSymbol[] = [];
  const exportedDeclarations = sourceFile.getExportedDeclarations();

  for (const [name, declarations] of exportedDeclarations) {
    for (const decl of declarations) {
      // Skip re-exports from other files
      if (decl.getSourceFile() !== sourceFile) continue;

      const kind = decl.getKind();
      let symbol: ExportedSymbol | null = null;

      if (kind === SyntaxKind.FunctionDeclaration) {
        const fn = decl as any;
        const params = fn.getParameters?.()?.map((p: any) => p.getText()).join(", ") ?? "";
        const returnType = fn.getReturnType?.()?.getText() ?? "void";
        symbol = {
          name,
          kind: "function",
          signature: `(${params}) => ${returnType}`,
          doc: getJsDoc(decl),
        };
      } else if (kind === SyntaxKind.ClassDeclaration) {
        symbol = {
          name,
          kind: "class",
          signature: `class ${name}`,
          doc: getJsDoc(decl),
        };
      } else if (kind === SyntaxKind.InterfaceDeclaration) {
        symbol = {
          name,
          kind: "interface",
          signature: `interface ${name}`,
          doc: getJsDoc(decl),
        };
      } else if (kind === SyntaxKind.TypeAliasDeclaration) {
        symbol = {
          name,
          kind: "type",
          signature: `type ${name}`,
          doc: getJsDoc(decl),
        };
      } else if (
        kind === SyntaxKind.VariableDeclaration ||
        kind === SyntaxKind.VariableStatement
      ) {
        symbol = {
          name,
          kind: "constant",
          signature: name,
          doc: "",
        };
      }

      if (symbol) {
        symbols.push(symbol);
      }
    }
  }

  return symbols;
}

function isBarrelFile(sourceFile: SourceFile): boolean {
  // A barrel file only re-exports and has no own declarations
  const statements = sourceFile.getStatements();
  for (const stmt of statements) {
    const kind = stmt.getKind();
    if (
      kind === SyntaxKind.ExportDeclaration ||
      kind === SyntaxKind.ImportDeclaration
    ) {
      continue;
    }
    // Any other statement means it has content
    return false;
  }
  // Must have at least one export declaration to be a barrel
  return sourceFile.getExportDeclarations().length > 0;
}

function extractEdges(
  sourceFile: SourceFile,
  root: string
): DependencyEdge[] {
  const edges: DependencyEdge[] = [];
  const sourceRel = relative(root, sourceFile.getFilePath());

  for (const imp of sourceFile.getImportDeclarations()) {
    const moduleSpecifier = imp.getModuleSpecifierValue();
    // Only track relative imports
    if (!moduleSpecifier.startsWith(".")) continue;

    const namedImports = imp
      .getNamedImports()
      .map((n) => n.getName());
    const defaultImport = imp.getDefaultImport()?.getText();
    const symbols = defaultImport
      ? [defaultImport, ...namedImports]
      : namedImports;

    // Resolve the target path
    const sourceDir = dirname(sourceFile.getFilePath());
    let targetPath = resolve(sourceDir, moduleSpecifier);

    // Try to find actual file
    const extensions = [".ts", ".tsx", ".js", ".jsx"];
    let resolved = targetPath;
    if (!existsSync(targetPath)) {
      for (const ext of extensions) {
        if (existsSync(targetPath + ext)) {
          resolved = targetPath + ext;
          break;
        }
      }
      // Check for index file
      if (resolved === targetPath && existsSync(join(targetPath, "index.ts"))) {
        resolved = join(targetPath, "index.ts");
      }
    }

    const targetRel = relative(root, resolved);
    edges.push({ source: sourceRel, target: targetRel, symbols });
  }

  return edges;
}

export function scan(options: ScanOptions): SourceGraph {
  const root = resolve(options.root);
  const tsConfigPath = options.tsConfigPath ?? join(root, "tsconfig.json");

  let project: Project;

  if (existsSync(tsConfigPath)) {
    project = new Project({ tsConfigFilePath: tsConfigPath });
  } else {
    project = new Project({ compilerOptions: { allowJs: true } });
    const include = options.include ?? ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"];
    for (const pattern of include) {
      project.addSourceFilesAtPaths(join(root, pattern));
    }
  }

  const exclude = options.exclude ?? DEFAULT_EXCLUDE;
  const units: SourceUnit[] = [];
  const edges: DependencyEdge[] = [];

  for (const sourceFile of project.getSourceFiles()) {
    const filePath = sourceFile.getFilePath();
    const relPath = relative(root, filePath);

    // Skip excluded directories
    if (exclude.some((ex) => relPath.includes(ex))) continue;
    // Skip declaration files
    if (relPath.endsWith(".d.ts")) continue;

    const exports = extractExports(sourceFile);
    const barrel = isBarrelFile(sourceFile);
    const language: "typescript" | "javascript" = relPath.endsWith(".ts") || relPath.endsWith(".tsx")
      ? "typescript"
      : "javascript";

    units.push({
      file: relPath,
      has_content: !barrel,
      exports,
      language,
    });

    edges.push(...extractEdges(sourceFile, root));
  }

  return {
    units,
    edges,
    root,
    language: "typescript",
  };
}
