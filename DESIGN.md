# Design

Ringside's visual system, recorded from the built product. Direction: **Halo**.

## The idea

**The app fills the viewport. The browser is already the window, so the product never draws another one.**

The direction began from a screenshot of a desktop app sitting on a wallpaper. The wallpaper was the
operating system, not the design; rebuilding it as a page background produced a window inside a window
and wasted a band of screen on every side. The ambient teal survives, but it lives in real surfaces:
a soft wash down the navigation rail, the icon tiles, focus rings, selection. Glass appears only where
something genuinely sits over content, which on the web means the mobile drawer, popovers and dialogs.
**Nothing is ever blurred behind the data**, because blur behind small text is where glassmorphism dies,
and this product is a table of call results a recruiter reads all day.

## Color

Strategy: **restrained**. Neutrals plus one ambient hue, with a strict state vocabulary.

| Role | Light | Dark | Notes |
| --- | --- | --- | --- |
| Ambient (rail wash) | `--tint` at 7% | `--tint` at 11% | a soft vertical wash down the rail, nowhere else |
| Tint (brand accent) | `#0E7F8A` | `#35A3AD` | focus rings, icon tiles, empty-state marks |
| Sheet (workspace) | `#FFFFFF` | `#191A1C` | never translucent, fills the viewport |
| Rail | `#F7FAFA` | `#131517` | solid, with the ambient wash on top |
| Glass (overlays only) | `rgb(255 255 255 / .82)` | `rgb(28 30 32 / .86)` | `blur(20px) saturate(160%)` |
| Ink (foreground) | `#191818` | `#ECEEEF` | |
| Action (primary) | `#1D1B19` | `#F0F2F2` | near-black, so the tint carries brand and buttons carry intent |

### Call-state vocabulary

Four states, each with a lamp, a word, and a colour. Colour is never the only signal.

| State | Light | Dark | Means |
| --- | --- | --- | --- |
| Live | `#DD9C10` | `#E9AB2E` | ringing or talking; the only animated element in the product |
| Done | `#2A7A38` | `#6CC25F` | completed |
| Fail | `#C9453E` | `#E2665F` | not connected or failed |
| Idle | muted foreground | muted foreground | scheduled, cancelled, not started |

**Why the green is `#2A7A38` and not an emerald.** The ambient teal sits at hue 185. A conventional
success green (`#15774F`) sits at 155, only 30° away, so score pills read as more frame rather than as
a signal. Rotating to grass at hue 130 puts 55° between them at the same lightness, so contrast against
white barely moves (5.6:1 → 5.3:1) while the meaning becomes unmistakable. Do not "correct" this back
toward emerald.

Amber is reserved for a live call and nothing else. That is why the ambient is teal rather than the
honey of the original reference: honey and an amber lamp are the same family, and a ringing
call would lose its urgency against its own background.

## Type

One family. **Onest** for everything, **Geist Mono** for time, duration, phone numbers and identifiers.
Monospace is used for measurement, never as a costume for "technical".

Product-UI scale: fixed rem steps, not fluid. Body sits at 13px with a tight ratio, because there are
more type elements here than on a brand surface and exaggerated contrast becomes noise.

## Surfaces and depth

- `.halo-rail` — the navigation rail: a solid surface with the ambient wash fading out over its top 42%.
- `.halo-glass` — frosted, `blur(20px) saturate(160%)`, for the mobile drawer, popovers and dialogs only.
  The saturation is what makes it read as glass rather than as a grey overlay.
- Radius: 10px throughout (`--radius`). No page-level rounding; the app meets the viewport edge.

## Motion

One authored moment: the live lamp pulses on an exponential ease-out while a call is ringing. Everything
else is a 150ms colour or opacity transition tied to a state change. No page-load choreography; the
product loads into a task. All motion respects `prefers-reduced-motion`.

## Theme

Light and dark are equal citizens. The default follows the visitor's OS via `prefers-color-scheme`, with
an explicit three-way override (light / system / dark) in the rail. A blocking inline script sets the
class before first paint so there is no flash; the choice is external state read through
`useSyncExternalStore`, not React state.

## Components

shadcn/ui over Base UI primitives, **restyled through tokens, never replaced**. Every shadcn token
(`--primary`, `--muted-foreground`, `--border`, `--sidebar`, …) is redefined in `globals.css`; the
component files in `src/components/ui` are stock. Halo adds its own token layer on top: `--sheet`,
`--rail`, `--hairline`, `--tint`, and the `live` / `done` / `fail` triplets, each exposed to Tailwind
through `@theme inline`.

Browser surfaces are themed too: selection, focus rings, and scrollbars all draw from the palette.
Tables use tabular numerals so figures align down a column.

## Rules that are easy to break by accident

1. The app is edge to edge. No frame, no page background, no rounded outer shell. A desktop wallpaper
   in a reference screenshot is the operating system, not the design.
2. Never put `backdrop-filter` behind a table, a form, or any block of small text.
3. Amber means a live call. Do not reuse it for warnings, highlights, or emphasis.
4. The primary action stays near-black. Hunar's blue (`#006EDD`) is reserved for surfaces that carry
   their name; it is a credit, not co-branding.
5. Cards do not nest. If a card needs cards inside it, the outer card should not exist.
6. State is a lamp plus a word. A colour on its own is not a state.
