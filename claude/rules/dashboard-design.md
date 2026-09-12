---
paths:
  - "src/**/*.tsx"
  - "src/**/*.css"
  - "dashboard/src/**/*.{tsx,css}"
  - "dashboards/*/src/**/*.{tsx,css}"
---

# Dashboard Design Rules

> Hard requirement for every dashboard you build. The goal: a Huitzo
> dashboard should look like Huitzo on first render — never a generic AI
> starter page someone has to redesign by hand. Read this before writing UI.

These rules cover the **visual** side. `react-patterns.md` covers the
engineering side (framework, structure, accessibility, security). Full token
and primitive reference: the `huitzo-dashboard-sdk` skill.

## Design tokens

- Use the brand-token CSS variables only, from
  `@huitzo/dashboard-sdk-react/styles` (imported once in `main.tsx`).
- ❌ Never write a hex color, RGB triple, or HSL value in component CSS — every color you need already exists as `var(--color-*)`.
- Spacing: `var(--space-0,1,2,3,4,5,6,8,10,12,16)` (a 4px scale — not every
  integer exists). Radius: `var(--radius-sm,md,lg,xl,2xl,full)`. Transitions:
  `var(--transition-fast,normal,slow)`.
- Shadows: only `--shadow-sm` and `--shadow-md` ship — there is no
  `--shadow-lg`. Don't author a new shadow; use one of these or rely on
  `hz-card`.
- Type scale: `--text-xs,sm,base,lg,xl,2xl,3xl`; weight
  `--font-normal,medium,semibold,bold`; line-height
  `--leading-tight,normal,relaxed`; family `--font-sans`, `--font-mono`.
- Tile-identity accents `--color-tile-1` … `--color-tile-8` exist
  specifically for `DashboardTile`/`resolveTileIdentity` — don't reach for
  them as general-purpose decoration.

## Primitives over custom CSS

Reach for `hz-*` classes from `@huitzo/dashboard-sdk-react/styles` before
writing CSS:

- `hz-card` (+ `--lg`, `--md`, `--accent`, `--success`, `--warning`)
- `hz-stat__number` (+ `--success`, `--warning`)
- `hz-rail`, `hz-step`, `hz-step__badge` for numbered onboarding flows
- `hz-terminal` (+ `__header`, `__dots`, `__dot`, `__label`, `__body`,
  `__prompt`, `__output`, `__copy`, `__copy--ok`)
- `hz-btn` (+ `--primary`, `--secondary`, `--ghost`)
- `hz-eyebrow` (+ `--accent`)
- `hz-kbd`, `hz-code`
- `hz-tf` / `hz-tf__*` — `TemplateFrame` chrome (`header`, `eyebrow`, `title`,
  `description`, `actions`, `status`, `body`, `evidence`, `evidence-link`,
  `evidence-meta`), used by the `Dashboard`/`Form` templates
- `hz-dashboard__*` — `Dashboard` template body (`content`, `section`,
  `section-title`, `metrics`, `metric`, `label`, `value`, `detail`,
  `table-wrap`, `table`, `list`, `notice`, `details`, `empty`)
- `hz-form__*` — `Form` template body (`field`, `description`, `error`,
  `submit`)

❌ **`hz-arch` does not exist.** No CSS ships for it — do not use `hz-arch`/`hz-arch__chip`/`hz-arch__dot`/`hz-arch__label` for architecture diagrams or anything else. Compose `hz-card` + `hz-rail` + plain flex/grid instead.

If a primitive you need is genuinely missing, compose the existing ones
rather than inventing new custom CSS.

## Typographic hierarchy

Three tiers. Always.

1. **Eyebrow** — `<p className="hz-eyebrow">SECTION LABEL</p>` above the headline.
2. **Headline** — semantic `<h1>` / `<h2>` with the brand font (inherits from
   `.huitzo-dashboard`).
3. **Body** — default paragraph; `var(--color-text-secondary)` for
   supporting copy.

Never lead with a body paragraph. Never use the same font weight for
everything.

## Color usage (accent budget)

- `--color-accent` appears at most **once per viewport** as a CTA or anchor —
  primary button, accent card, or `hz-eyebrow--accent`.
- `--color-success` / `--color-warning` / `--color-error` are reserved for
  state, not decoration. Don't paint a hero green.
- Backgrounds are layered: `--color-bg-primary` (page) →
  `--color-bg-secondary` (sections) → `--color-bg-elevated` (cards).

## Spacing rhythm

- Generous whitespace beats dense layouts. Vertical gap between major
  sections is `var(--space-12)` minimum.
- Cards use `hz-card--lg` (32px) for hero content, `hz-card--md` (24px) for
  grids.
- Don't pack the viewport. Empty space is part of the design.

## Theme awareness

- The root component MUST wrap children in `<div className="huitzo-dashboard">`
  — this scopes the brand tokens; without it they don't resolve.
- Every color must resolve via a token so it adapts to `data-theme="light"`
  automatically.
- Test both themes — if something only looks right in dark, a hex color is
  leaking somewhere.

### Dark/light verification

Before calling a dashboard done:

1. Open it in the dev server (`/dashboard-dev`).
2. Screenshot in dark theme.
3. Toggle the Hub theme to light and screenshot again.
4. Both must look intentional. Washed-out light usually means a hardcoded
   color, not a token problem.

## Anti-patterns

Never:

- ❌ Import a UI kit (Material UI, Ant Design, Chakra, shadcn/ui, Radix-styled). Primitives + tokens only, or the copy-in `@huitzo/dashboard-primitives` registry via `huitzo primitives add`.
- ❌ Use a hex literal in a Tailwind class (`bg-[#155dfc]`). Use `bg-[var(--color-accent)]` if you must, or better, `hz-btn--primary`.
- ❌ Add an animation library (framer-motion, react-spring). Use `--transition-fast` / `--transition-normal`.
- ❌ Author a hardcoded `box-shadow: 0 4px ...`. Use `--shadow-sm`/`-md` or rely on `hz-card`.
- ❌ Render the AI-default landing page: a centered `<h1>` "Welcome to {dashboard-name}", one subtitle paragraph, and a blue gradient button. These rules exist to prevent exactly that.
- ❌ Use `dangerouslySetInnerHTML` without sanitization.
- ❌ Skip the `huitzo-dashboard` wrapper class — brand tokens will not resolve.
- ❌ Reference `hz-arch` in any form — it ships no CSS.

## See also

- `react-patterns.md` — engineering rules for dashboard React/TypeScript code.
- `hub-contract.md` — the `mount`/`unmount` + `HuitzoProvider` contract.
