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
| Page | `#F3F6F7` | `#141618` | the plane cards sit on; fills the viewport |
| Card | `#FFFFFF` | `#1E2124` | the lifted plane, 1.1:1 against the page |
| Rail | `#EDF3F4` | `#0F1113` | solid, with the ambient wash on top |
| Glass (overlays only) | `rgb(255 255 255 / .86)` | `rgb(32 35 38 / .88)` | `blur(20px) saturate(160%)` |
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

Three planes, always in the same order: **rail behind, page in the middle, cards lifted**. A card is
never the same value as the page. In light that means a receded grey page with true-white cards over a
real shadow; in dark it inverts, because you raise a surface with light, not with shade, so the card
fill goes lighter and the shadow disappears. One token, `--card-shadow`, carries both cases.

The elevation is applied to `[data-slot="card"]` so every shadcn Card inherits it untouched, and to a
`.surface` class for the containers we author ourselves (tables, the dashboard entry panels).

- `.halo-rail` — the navigation rail: a solid surface with the ambient wash fading out over its top 42%.
- `.halo-glass` — frosted, `blur(20px) saturate(160%)`. **Chrome only**: bars and rails that overlap
  scrolling content and carry no reading text, which in practice is the mobile header. The saturation
  is what makes it read as glass rather than as a grey overlay.
- `--popover` is **opaque** and one step above the card, so menus, dialogs and drawers float on shadow
  rather than on alpha. A translucent menu over a table is an unreadable menu.
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

## The mark

A voice waveform bent into a ring: twelve radial ticks on a 24 grid, inner radius 5.7, stroke 1.95,
round caps, drawn in `--tint`. The wordmark is `ringside`, lowercase, Onest 500 at −0.032em, so the mark
stays the loudest element and carries the meaning.

The tick count and weight are load-bearing. The first draft used twenty-two hairlines and fused into a
solid disc at favicon size; twelve heavier ticks with round caps survive 16px. Do not add ticks or thin
the stroke. Lives in `src/components/logo.tsx`, with `app/icon.svg` for the favicon and `app/apple-icon.tsx`
rendering the home-screen tile as the mark knocked out of the Halo gradient. The favicon is drawn at
stroke 2.5 rather than the in-app 1.95, because 16px eats weight.

**Browser tabs carry the screen name only** — "Dashboard", "Calls", "New job" — with no brand prefix.
The favicon carries the brand. Tab titles truncate early, so a prefix spends the visible characters on
what the reader already knows and hides where they are; it also makes several open tabs identical.
Client pages cannot export metadata, so each route segment holds a small `layout.tsx` that does.

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
2. `--card` and `--page` are never the same value. If a card needs a hairline to be visible at all,
   the elevation is missing, not the border.
3. Never put `backdrop-filter` or alpha behind a table, a form, a menu, or any block of reading text.
   Overlays earn their separation from shadow and an opaque fill, never from transparency.
4. Amber means a live call. Do not reuse it for warnings, highlights, or emphasis.
5. The primary action stays near-black. Hunar's blue (`#006EDD`) is reserved for surfaces that carry
   their name; it is a credit, not co-branding.
6. Cards do not nest. If a card needs cards inside it, the outer card should not exist.
7. State is a lamp plus a word. A colour on its own is not a state.
