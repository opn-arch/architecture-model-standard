#!/usr/bin/env node
const { scan } = require("../dist/scan");
const { writeFileSync, mkdirSync } = require("fs");
const { resolve, join, dirname } = require("path");

const root = resolve(process.argv[2] || ".");
const output = process.argv[3] || join(root, ".architecture-models", "source-graph.json");

console.log(`Scanning: ${root}`);
const graph = scan({ root });
console.log(`  Files: ${graph.units.length}`);
console.log(`  Dependencies: ${graph.edges.length}`);
console.log(`  Exports: ${graph.units.reduce((acc, u) => acc + u.exports.length, 0)}`);

mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, JSON.stringify(graph, null, 2));
console.log(`  Output: ${output}`);
