// Reads ../backend/home_scanner/locations.yml and writes lib/locations.json.
// Runs as `prebuild` so Vercel always picks up the latest YAML.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "yaml";

const here = dirname(fileURLToPath(import.meta.url));
const yamlPath = join(here, "..", "..", "backend", "home_scanner", "locations.yml");
const outPath = join(here, "..", "lib", "locations.json");

const entries = parse(readFileSync(yamlPath, "utf-8"));
const compact = entries.map((e) => ({
  name: e.name,
  url_slug: e.url_slug,
}));

writeFileSync(outPath, JSON.stringify(compact, null, 2) + "\n");
console.log(`Wrote ${compact.length} locations to ${outPath}`);
