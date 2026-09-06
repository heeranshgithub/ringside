/*
  Guards the pointer-cursor rule against the one way it realistically breaks.

  Tailwind v4 dropped Preflight's `button { cursor: pointer }`, so this app restores it as a
  role-based rule in globals.css. Two things can silently undo that:

    1. The base rule is edited away or renamed.
    2. `shadcn add select` (or dropdown-menu) overwrites the vendored component and brings
       back the upstream `cursor-default` on menu items, which outranks a base-layer rule
       because utilities win over base.

  Neither shows up in tsc, eslint or a build. Both show up here.

  Note the assertions on the inputs themselves. A checker that silently reads zero files
  passes forever while testing nothing, which is a more expensive failure than the bug.
*/
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const UI_DIR = "src/components/ui";
const CSS = "src/app/globals.css";

// Interactive parts that must not carry `cursor-default`. Keyed by the file they live in,
// with the class fragment that identifies the item (as opposed to a scroll arrow, which is
// a hover-scroll affordance and keeps the arrow deliberately).
const ITEM_MARKER = "items-center gap-1.5";

const failures = [];

const css = readFileSync(CSS, "utf8");
if (!css.includes("cursor: pointer")) {
  failures.push(`${CSS}: the base cursor rule is gone. Buttons will show an arrow again.`);
}
for (const role of [
  '[role="option"]',
  '[role="menuitem"]',
  '[role="checkbox"]',
  '[role="switch"]',
  '[role="tab"]',
]) {
  if (!css.includes(role)) {
    failures.push(
      `${CSS}: the base cursor rule no longer covers ${role}. Base UI renders that part as a div or span, so dropping it leaves those controls with an arrow.`,
    );
  }
}

const files = readdirSync(UI_DIR).filter((f) => f.endsWith(".tsx"));
if (files.length < 10) {
  throw new Error(
    `only ${files.length} files found in ${UI_DIR}; the scan is looking in the wrong place`,
  );
}

let itemsChecked = 0;
for (const file of files) {
  const text = readFileSync(join(UI_DIR, file), "utf8");
  for (const [i, line] of text.split("\n").entries()) {
    if (!line.includes(ITEM_MARKER)) continue;
    itemsChecked++;
    if (line.includes("cursor-default")) {
      failures.push(
        `${UI_DIR}/${file}:${i + 1}: an interactive item carries \`cursor-default\`, which overrides the base pointer rule. This is how shadcn ships it; remove it again.`,
      );
    }
  }
}
if (itemsChecked === 0) {
  throw new Error(
    `no interactive items matched "${ITEM_MARKER}"; the marker is stale and this check is inspecting nothing`,
  );
}

if (failures.length > 0) {
  console.error(`cursor rules: ${failures.length} problem(s)\n`);
  for (const f of failures) console.error(`  - ${f}`);
  process.exit(1);
}
console.log(
  `cursor rules ok (base rule present, ${itemsChecked} interactive items clean across ${files.length} components)`,
);
