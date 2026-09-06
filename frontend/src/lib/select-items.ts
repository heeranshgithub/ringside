/**
 * Build the `items` map a Base UI `<Select.Root>` needs to show a label in its trigger.
 *
 * Without it `<Select.Value>` renders the raw `value`, so any select keyed by an id displays
 * a UUID where a name belongs. It is invisible on selects whose value *is* the label — "10",
 * "all" — which is why it survived so long on the ones keyed by `job.id` and `agent.id`.
 *
 * Pass the same `label` function used to render the options, so the trigger and the list
 * cannot drift apart when one of them is edited.
 */
export function selectItems<T>(
  rows: readonly T[],
  value: (row: T) => string,
  label: (row: T) => string,
  extra?: Record<string, string>,
): Record<string, string> {
  return { ...extra, ...Object.fromEntries(rows.map((row) => [value(row), label(row)])) };
}
