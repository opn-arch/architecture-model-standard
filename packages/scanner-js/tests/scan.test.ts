import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { mkdirSync, writeFileSync, rmSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { scan } from "../src/scan.js";

const TEST_DIR = join(tmpdir(), "arch-scanner-test-" + Date.now());

beforeAll(() => {
  mkdirSync(join(TEST_DIR, "src"), { recursive: true });

  writeFileSync(
    join(TEST_DIR, "tsconfig.json"),
    JSON.stringify({
      compilerOptions: {
        target: "ES2022",
        module: "Node16",
        moduleResolution: "Node16",
        strict: true,
        rootDir: "./src",
        outDir: "./dist",
      },
      include: ["src/**/*"],
    })
  );

  writeFileSync(
    join(TEST_DIR, "src/utils.ts"),
    `/**
 * A helper function.
 */
export function helper(): string {
  return "hello";
}

export class Config {
  value: number = 0;
}

export const VERSION = "1.0.0";
`
  );

  writeFileSync(
    join(TEST_DIR, "src/main.ts"),
    `import { helper, Config } from "./utils";

export function main(): void {
  const cfg = new Config();
  console.log(helper());
}
`
  );

  writeFileSync(
    join(TEST_DIR, "src/index.ts"),
    `export { helper, Config } from "./utils";
export { main } from "./main";
`
  );
});

afterAll(() => {
  rmSync(TEST_DIR, { recursive: true, force: true });
});

describe("scan", () => {
  it("finds all source files", () => {
    const graph = scan({ root: TEST_DIR });
    expect(graph.units.length).toBe(3);
    const files = graph.units.map((u) => u.file);
    expect(files).toContain("src/utils.ts");
    expect(files).toContain("src/main.ts");
    expect(files).toContain("src/index.ts");
  });

  it("extracts exports with signatures", () => {
    const graph = scan({ root: TEST_DIR });
    const utils = graph.units.find((u) => u.file === "src/utils.ts")!;
    expect(utils.exports.length).toBeGreaterThanOrEqual(3);
    const helperExport = utils.exports.find((e) => e.name === "helper");
    expect(helperExport).toBeDefined();
    expect(helperExport!.kind).toBe("function");
    expect(helperExport!.signature).toContain("string");
  });

  it("captures dependency edges", () => {
    const graph = scan({ root: TEST_DIR });
    const mainEdges = graph.edges.filter((e) => e.source === "src/main.ts");
    expect(mainEdges.length).toBeGreaterThanOrEqual(1);
    expect(mainEdges[0].target).toContain("utils");
    expect(mainEdges[0].symbols).toContain("helper");
  });

  it("detects barrel files (has_content=false)", () => {
    const graph = scan({ root: TEST_DIR });
    const index = graph.units.find((u) => u.file === "src/index.ts")!;
    expect(index.has_content).toBe(false);
  });
});
