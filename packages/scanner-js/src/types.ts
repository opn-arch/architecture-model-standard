export interface ExportedSymbol {
  name: string;
  kind: "function" | "class" | "constant" | "type" | "interface";
  signature: string;
  doc: string;
}

export interface SourceUnit {
  file: string;
  has_content: boolean;
  exports: ExportedSymbol[];
  language: "typescript" | "javascript";
}

export interface DependencyEdge {
  source: string;
  target: string;
  symbols: string[];
}

export interface SourceGraph {
  units: SourceUnit[];
  edges: DependencyEdge[];
  root: string;
  language: string;
}

export interface ScanOptions {
  root: string;
  tsConfigPath?: string;
  include?: string[];
  exclude?: string[];
  followReExports?: boolean;
}
