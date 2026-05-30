---
paths:
  - "src/**/*.tsx"
  - "src/**/*.ts"
  - "src/**/*.css"
---

# Dashboard Design Rules

> Hard requirement for every dashboard you build. The goal: a Huitzo dashboard
> should look like Huitzo on first render — never like a generic AI starter page
> that someone has to redesign by hand. Read this before writing any UI.

These rules cover the **visual** side. `react-patterns.md` covers the
engineering side (framework, structure, accessibility, security).

## Design tokens

- Use the brand-token CSS variables only. They are re-exported from
  `@huitzo/dashboard-sdk-react/styles` — import that stylesheet once in
  `src/main.tsx` (and your dev entry).
- **Never** write a hex color, RGB triple, or HSL value in component CSS. If you
  need a color, it already exists as `var(--color-*)`.
- Spacing uses `var(--space-*)` (a 4px scale). Border radius uses
  `var(--radius-*)`. Transitions use `var(--transition-*)`.
- Shadows: prefer the existing `--shadow-sm` / `--shadow-md`. Do not author new
  shadows; the cards already carry one.

## Primitives over custom CSS

Reach for the `hz-*` classes from `@huitzo/dashboard-sdk-react/styles` before
writing CSS:

- `hz-card` (+ `--lg`, `--md`, `--accent`, `--success`, `--warning`)
- `hz-stat__number` (+ `--success`, `--warning`)
- `hz-rail`, `hz-step`, `hz-step__badge` for numbered onboarding flows
- `hz-terminal` (+ `__header`, `__dots`, `__label`, `__body`, `__prompt`, `__output`, `__copy`)
- `hz-btn` (+ `--primary`, `--secondary`, `--ghost`)
- `hz-eyebrow` (+ `--accent`)
- `hz-kbd`, `hz-code`
- `hz-arch` (+ `__chip`, `__dot`, `__label`) for architecture diagrams

If a primitive you need is missing, compose existing ones rather than
re-inventing custom styling.

## Typographic hierarchy

Three tiers. Always.

1. **Eyebrow** — `<p className="hz-eyebrow">SECTION LABEL</p>` above the headline.
2. **Headline** — semantic `<h1>` / `<h2>` with the brand font (inherits from
   `.huitzo-dashboard`).
3. **Body** — default paragraph; use `var(--color-text-secondary)` for
   supporting copy.

Never lead with a body paragraph. Never use the same font weight for everything.

## Color usage (accent budget)

- The accent color (`--color-accent`) appears at most **once per viewport** as a
  CTA or anchor — primary button, accent card, or `hz-eyebrow--accent`.
- Status colors (`--color-success`, `--color-warning`, `--color-error`) are
  reserved for state, not decoration. Don't paint a hero green.
- Backgrounds are layered: `--color-bg-primary` (page) →
  `--color-bg-secondary` (sections) → `--color-bg-elevated` (cards).

## Spacing rhythm

- Generous whitespace beats dense layouts. The vertical gap between major
  sections is `var(--space-12)` minimum.
- Cards use `hz-card--lg` (32px) for hero content, `hz-card--md` (24px) for
  grids.
- Don't pack the viewport. Empty space is part of the design.

## Theme awareness

- Your root component MUST wrap children in `<div className="huitzo-dashboard">`.
  This scopes the brand tokens so they resolve.
- Every color you use MUST resolve via the token system so it adapts to
  `data-theme="light"` automatically.
- Test both themes. If something only looks right in dark, you have a hex color
  leaking somewhere.

### Dark/light verification

Before claiming a dashboard is done:

1. Open it in the dev server (`/dashboard-dev`).
2. Screenshot in dark theme.
3. Toggle the Hub theme to light and screenshot again.
4. Both must look intentional. If light looks washed out, the cause is a
   hardcoded color, not the tokens.

## Anti-patterns

Never:

- Import a UI kit (Material UI, Ant Design, Chakra, shadcn/ui, Radix-styled).
  Primitives + tokens only.
- Use hex literals in Tailwind class names (`bg-[#155dfc]`). Use
  `bg-[var(--color-accent)]` if you must, or better, use `hz-btn--primary`.
- Add an animation library (framer-motion, react-spring). Use CSS transitions on
  `--transition-fast` / `--transition-normal`.
- Author hardcoded shadows (`box-shadow: 0 4px ...`). Use the `--shadow-*`
  tokens or rely on `hz-card`.
- Render the AI-default landing page: a centered `<h1>` "Welcome to
  {dashboard-name}", a single subtitle paragraph, and a blue gradient button.
  That is the look these rules exist to prevent.
- Use `dangerouslySetInnerHTML` without sanitization (XSS).
- Skip the `huitzo-dashboard` wrapper class — without it, the brand tokens do
  not resolve.

## See also

- `react-patterns.md` — engineering rules for dashboard React/TypeScript code.
- `hub-contract.md` — the `mount`/`unmount` + `HuitzoProvider` contract.
