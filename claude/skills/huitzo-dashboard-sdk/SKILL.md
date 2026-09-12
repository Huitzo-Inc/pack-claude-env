---
name: huitzo-dashboard-sdk
description: "@huitzo/dashboard-sdk-react hooks, components, templates, and tokens. Use when writing or reviewing Huitzo Dashboard UI. Not for pack commands (huitzo-sdk) or CLI usage (cli-non-interactive)."
---

> Verified against @huitzo/dashboard-sdk-react 5.1.1 / @huitzo/dashboard-sdk 0.6.0 (2026-09).

A Huitzo Dashboard is a React micro-frontend that Hub loads as an isolated module. This skill covers the client SDK a dashboard author writes against: the module contract, the React provider/hooks, the components and templates, and the shipped design tokens.

## Install

```bash
npm install @huitzo/dashboard-sdk-react@^5.1.1
```

`@huitzo/dashboard-sdk` (core, 0.6.0+) is a peer dependency and gets installed transitively — you rarely import it directly. Peer requirements: `@huitzo/dashboard-sdk >=0.6.0`, `react >=19.0.0`, `react-dom >=19.0.0`. Both packages are **runtime** dependencies (bundled into your `dist/main.js`, not shared with Hub).

## Module contract

`src/main.tsx` exports exactly two named functions — this is what Hub's `import()` calls:

```typescript
export function mount(container: HTMLElement, context: HuitzoMountContext): void;
export function unmount(container: HTMLElement): void;
```

Mandatory shape:

```typescript
import { createRoot, type Root } from 'react-dom/client';
import { HuitzoProvider, type HuitzoMountContext } from '@huitzo/dashboard-sdk-react';
import '@huitzo/dashboard-sdk-react/styles';   // once — tokens + hz-* primitives
import App from './App';

let root: Root | null = null;

export function mount(container: HTMLElement, context: HuitzoMountContext): void {
  root = createRoot(container);
  root.render(
    <HuitzoProvider context={context}>
      <div className="huitzo-dashboard">
        <App />
      </div>
    </HuitzoProvider>,
  );
}

export function unmount(_container: HTMLElement): void {
  root?.unmount();
  root = null;
}
```

- **`HuitzoProvider` is mandatory.** Every hook in this package calls `useHuitzo()` internally, which throws `HuitzoError("useHuitzo must be used within <HuitzoProvider>")` when rendered outside one.
- **The `.huitzo-dashboard` wrapper class is mandatory.** Brand tokens and `hz-*` primitives resolve under it; without it, `var(--color-*)` reads as nothing.
- **Import `@huitzo/dashboard-sdk-react/styles` exactly once** (in `main.tsx`, mirrored in your dev entry). It is a separate subpath export (`dist/styles/tokens.css`), not part of the `index.ts` barrel.

## `HuitzoMountContext`

The vanilla object Hub passes to `mount()` (re-exported type alias for the core `HuitzoContext`):

| Field | Type | Notes |
|---|---|---|
| `apiUrl` | `string` | Backend API base URL |
| `getToken` | `() => string` | **Getter, not a property** — call it fresh each time you need the JWT |
| `slug` | `string` | This dashboard's slug |
| `sdkVersion` | `string` | Hub's SDK version |
| `user` | `{ id, email, name?, roles: string[], tenantId }` | |
| `theme?` | `"light" \| "dark"` | Optional — degrades to a `data-theme` MutationObserver when absent |
| `locale?` | `string` | BCP-47, optional — `useLocale`/`useHubContext` fall back to `en-US` |
| `currency?` | `string` | ISO 4217, optional |
| `navigate` | `(path: string) => void` | In-Hub navigation |
| `navigateToHub` | `() => void` | Return to Hub home |
| `navigateToDashboard` | `(slug: string) => void` | Jump to another dashboard |
| `showNotification` | `(message, type: "info"\|"error"\|"success") => void` | |
| `on` | `(event: string, handler: (data: unknown) => void) => () => void` | Returns an unsubscribe function |
| `emit` | `(event: string, data: unknown) => void` | |

**`getToken` supply-chain note:** it is a function, not a stored string, specifically so a bundled third-party dependency can't passively read the JWT off a plain object. Call it only from your own code path right before a request; never log it, store it, or pass it into a third-party callback. Audit your lockfile and consider `--ignore-scripts` for the same reason `HuitzoProvider` never exposes it as a prop.

`HuitzoProvider` calls `context.getToken()` for you on mount and re-syncs only when the value changes (JWT rotation) — you should not call `getToken()` yourself unless you are talking to a non-SDK endpoint.

## `HuitzoProvider`

```typescript
interface HuitzoProviderProps {
  context: HuitzoMountContext;
  onAuthError?: (error: Error) => void;
  children: ReactNode;
}
```

Creates one `HuitzoClient` on first render (later context changes are ignored — recreating the client would drop auth state). On mount, if a token is present, fetches the user, then the installed-packs list — sequentially, not in parallel; a 401 from the user fetch clears auth and calls `onAuthError`; any other fetch error is aggregated into `initError` (both errors, not just the last one).

`useHuitzo(): HuitzoContextValue` is the gateway hook every other hook calls internally:

```typescript
{ client: HuitzoClient; user: UserInfo | null; isAuthenticated: boolean;
  initError: Error | null; mountContext: HuitzoMountContext; packs: PackInfo[];
  isPackInstalled: (packId: string) => boolean }
```

## Hooks

### `useCommand` — the most-used hook

Two overloads, one implementation:

```typescript
// Typed (via @huitzo/dashboard-codegen CommandRef) — infers TInput/TOutput
useCommand<TInput extends Record<string, unknown>, TOutput>(
  ref: CommandRef<TInput, TOutput>,
  options?: TypedUseCommandOptions<TInput, TOutput>,
): TypedUseCommandReturn<TInput, TOutput>;

// Magic-string — you supply T
useCommand<T = unknown>(commandId: string, options?: UseCommandOptions<T>): UseCommandReturn<T>;
```

Return shape:

```typescript
{
  execute: (args?: Record<string, unknown>) => Promise<void>;
  data: T | null;
  loading: boolean;                // true for BOTH "loading" AND "polling"
  error: Error | null;
  reset: () => void;
  status: 'idle' | 'loading' | 'polling' | 'success' | 'error';
  isIdle: boolean; isPolling: boolean; isSuccess: boolean; isError: boolean;
}
```

State machine: `idle --execute()--> loading`. A command backed by a fast queue resolves `loading --(200)--> success | error` directly. A medium/long-queue command instead gets a **202 dispatch receipt**, moves to `polling`, and the hook polls the task until it reaches a terminal state — `polling --terminal--> success | error`. A 202 receipt is never surfaced as `data` and never cached; only the resolved terminal result is. A task that finishes non-`success` raises a `CommandError` built from the task's error. `reset()` returns to `idle` from any state.

Options: `onSuccess?`, `onError?`, `cacheTime?` (per-instance in-memory TTL, ms), `maxCacheSize?` (default `20`), `initialArgs?` (auto-execute on mount), `refetchInterval?` (`number | (data) => number`; pauses while the tab is hidden, fires one catch-up run on becoming visible again if due).

```typescript
const { execute, data, loading, error, status, isPolling, reset } =
  useCommand<ResultType>('@scope/pack/command');

useEffect(() => { execute({ id }); }, [execute, id]);

if (loading) return isPolling ? <QueuedState /> : <LoadingSpinner />;
if (error) return <ErrorMessage error={error} onRetry={() => execute({ id })} />;
if (!data) return <Empty />;
return <ResultView data={data} />;
```

### The rest of the hook set

| Hook | Signature / return | Notes |
|---|---|---|
| `useHuitzo()` | `HuitzoContextValue` | See above. Throws outside `HuitzoProvider`. |
| `useHubContext()` | `{ apiUrl, dashboardSlug, user, theme, locale, currency }` | Reactive: updates on `theme-change`/`locale-change` events. |
| `useLocale()` | `{ locale, currency, numberFormat, dateTimeFormat, relativeFormat }` | `Intl` formatters for the active locale — **not** an i18n `t()` function. Falls back to `en-US` if the active locale/currency throws. |
| `useHubNavigation()` | `{ navigateToHub, navigateToDashboard, navigateToExplore, navigateToSettings, currentDashboard }` | `navigateToExplore`/`navigateToSettings` call `mountContext.navigate()` with fixed paths. |
| `useRealtime(event, callback)` | `void` | See "Realtime" below. |
| `useHubActions()` | `{ showNotification({message,variant,duration?}), showConfirmDialog({title,body,...}) => Promise<boolean>, openSettings() }` | Dashboard → Hub direction. `showConfirmDialog` resolves `false` on timeout/unmount, rejects on abort. |
| `useHubBreadcrumbs(items)` | `void` | `items: { label: string; href?: string }[]`. Emits on change, clears on unmount. Unsafe `href`s are dropped. |
| `useStreamingCommand(commandId, options?)` | see below | Token-by-token / SSE command output. |
| `useConnectionStatus()` | always **throws** | Deferred stub — the WebSocket layer to pack backends isn't built. Use `useRealtime` for Hub-emitted events instead. |
| `usePacks()` | `{ packs, loading, error, isInstalled(packId), refetch() }` | Seeds from `HuitzoProvider`'s cache; only fetches if that cache is empty. |

`useStreamingCommand<TResult>(commandId, options?)`:

```typescript
{
  start: (args?) => Promise<void>; abort: () => void; reset: () => void;
  chunks: string[]; text: string;              // text = chunks.join("")
  result: TResult | null; error: Error | null;
  status: 'idle' | 'streaming' | 'success' | 'error';   // NO 'loading'
  isIdle: boolean; isStreaming: boolean; isSuccess: boolean; isError: boolean;
}
```
Options: `onToken?`, `onComplete?`, `onError?`, `timeoutMs?`. A 401 classifies as `AuthenticationError`, 403 as `AuthorizationError` (both re-exported from this package for `instanceof` checks); a 405 means the command doesn't declare streaming support.

### Realtime is an event bus, not a socket

`useRealtime<T>(event: string | string[], callback: (data: T) => void): void` subscribes via `mountContext.on()` on mount and auto-unsubscribes on unmount or when the event set changes. It runs over the **per-mount Hub event bus** — it does **not** open or require a WebSocket connection. Known event names (`HubEventName`, not exhaustive): `theme-change`, `navigation`, `viewport-resize`, `locale-change`, plus any pack-level event Hub re-emits.

## Components

**`<DashboardTile>`** — requires exactly one of `onClick` or `href` (never both, never neither):

```typescript
type DashboardTileProps =
  { name: string; description?: string; icon?: string; isPinned?: boolean;
    color?: string; className?: string; allowInsecureHttp?: boolean } &
  ({ onClick: () => void; href?: never } | { href: string; onClick?: never });
```
`href` is checked by `isSafeHref` — non-`https://` (unless `allowInsecureHttp`), protocol-relative `//`, and backslash-smuggled-authority URLs are rejected. `color` accepts a brand token (preferred), and also a raw hex/rgb/hsl as an escape hatch (hex emits a dev-mode console warning nudging toward tokens, but is not blocked); values matching `url(`, `expression`, `image-set`, `element(`, or injection characters are dropped to the default accent.

**`<DashboardInfoBlock>`**: `{ title, description?, icon?, metadata?: {label,value}[], variant?: "default"|"elevated"|"outlined", className? }`.

**`<TileGlyphIcon glyphId size? className?>`**: renders one of 10 geometric 24×24 `stroke=currentColor` glyphs — `square, circle, triangle, diamond, hexagon, plus, chevron, asterisk, zigzag, pentagon`.

**Tile identity** (deterministic fallback, no author-declared icon needed): `resolveTileIdentity(scope: string, slug: string): TileIdentity` hashes `${scope}/${slug}` (FNV-1a) to pick an accent token from `TILE_ACCENT_TOKENS` (`--color-tile-1`…`--color-tile-8`) and a glyph id from `TILE_GLYPH_IDS`, decorrelated so accent and glyph don't move in lockstep across a grid.

## Templates (5.1.0+)

`Dashboard` and `Form` are default, opinionated compositions over a frozen contract — use them for the common case; drop to `TemplateFrame` + your own layout when a page doesn't fit the "one command → one result" shape.

- **`TemplateFrame`** — shared chrome: eyebrow, exactly one `h1`/`h2`, description, actions, status, body, evidence. Renders the `hz-tf__*` classes.
- **`useTemplateCommand(ref, options?)`** — adapts the typed `useCommand` into a `TemplateCommandAdapter` (`{ status, data, error, execute, reset }`) that templates consume as their transport seam. `status` is a discriminated union: `{status:"idle"}` / `{status:"loading", progress?}` / `{status:"success"}` / `{status:"error", error}`.
- **`Dashboard`** — result-rendering template: `title`, `eyebrow?`, either a typed `command` (`CommandRef`) or a hand-built `adapter`, `sections?` (`ResultSection[]` or a function of the result), `evidence?`, `primaryAction?`.
- **`Form`** — `fields: FormFieldFor<TValues>[]`, `validation?`, `defaultValues?`, `toArgs?` (required when your form values don't match the command's input shape), `customField?` slot.
- **`FormFieldSpec`** types: `text | email | password | textarea | number | select` — **no `file` type** (deferred pending an upload/security gate; build your own upload flow outside `Form` if you need one).
- A custom `Form` field (`customField` slot) receives `{ field, value, error?, setValue, fieldId, describedById? }` — put `fieldId` on the control you want `Form`'s own generated `<label>` to point at.

Use `Dashboard`/`Form` when your page is "run a command, show/collect structured data." Hand-roll `App.tsx` + hooks directly when you need custom layout, multiple independent commands on one screen, or a visual design the templates' frame doesn't accommodate.

## Core client (non-React use)

`@huitzo/dashboard-sdk`'s `HuitzoClient` is what `HuitzoProvider` wraps; use it directly outside React (e.g. a Node script or a non-React micro-frontend):

```typescript
const client = new HuitzoClient({ apiUrl, timeout: 60_000 });
client.setToken(getToken());

const result = await client.commands.execute('@scope/pack/command', args);
if (isCommandReceipt(result)) {
  const task = await client.tasks.poll(result.task_id);   // capped-exponential backoff
} else {
  console.log(result.result);   // CommandResult<T> — no `.data` wrapper
}
```

- `client.commands.execute<T>(namespace, args?, {timeout?, signal?})` returns `CommandResult<T> | CommandReceipt` — narrow with `isCommandReceipt()` before reading `.result`.
- `client.tasks.get/cancel/poll(taskId, options?)` — `poll` options: `initialIntervalMs` (default 500), `maxIntervalMs` (default 5000), `maxWaitMs` (default 300 000, hard ceiling 1 800 000). `NotFoundError`/`AuthorizationError`/`TaskExpiredError`/`CancelledError` are terminal and never retried.
- `client.packs.list()` — `PackInfo[]`.
- Error hierarchy (all extend `HuitzoError`): `AuthenticationError`, `AuthorizationError`, `NotFoundError`, `ValidationError`, `TimeoutError`, `RateLimitError`, `CancelledError`, `NetworkError`, `CommandError`, `TaskExpiredError`, `InternalError`, `IntegrationError`, `ServiceUnavailableError`.

## Styles: tokens and `hz-*` primitives

Import once: `import '@huitzo/dashboard-sdk-react/styles'`. Tokens live in a layered `@layer huitzo-tokens` block — a host (Hub) defining the same custom property unlayered always wins, so white-labeling never needs an override war.

**Token families actually shipped** — use these, never a literal:

| Family | Values |
|---|---|
| Backgrounds | `--color-bg-primary`, `-secondary`, `-tertiary`, `-elevated` |
| Text | `--color-text-primary`, `-secondary`, `-muted`, `-inverse` |
| Border | `--color-border`, `--color-border-focus` |
| Accent | `--color-accent`, `-hover`, `-light`; `--color-accent-secondary`, `-hover` |
| On-accent | `--color-on-accent` (fixed white — for accent-filled surfaces, does not flip with theme) |
| Status | `--color-success`/`-light`, `--color-warning`/`-light`, `--color-error`/`-light`/`-hover`, `--color-info`/`-light` |
| Tile accents | `--color-tile-1` … `--color-tile-8` (contrast-verified, dark/light pairs) |
| Spacing | `--space-0,1,2,3,4,5,6,8,10,12,16` (4px scale — not every integer) |
| Font family | `--font-sans`, `--font-mono` |
| Type scale | `--text-xs,sm,base,lg,xl,2xl,3xl` |
| Weight | `--font-normal,medium,semibold,bold` |
| Line height | `--leading-tight,normal,relaxed` |
| Radius | `--radius-sm,md,lg,xl,2xl,full` |
| Shadow | `--shadow-sm`, `--shadow-md` **only — there is no `--shadow-lg`** |
| Transition | `--transition-fast,normal,slow` |

Dark is the default (`:root`); light overrides apply under `[data-theme="light"], :root.light`.

**`hz-*` primitive classes actually shipped:**

| Family | Members |
|---|---|
| Card | `.hz-card` + `--lg`, `--md`, `--accent`, `--success`, `--warning` |
| Stat | `.hz-stat__number` + `--success`, `--warning` |
| Onboarding rail | `.hz-rail`, `.hz-step`, `.hz-step__badge` |
| Terminal | `.hz-terminal` + `__header`, `__dots`, `__dot`, `__label`, `__body`, `__prompt`, `__output`, `__copy`, `__copy--ok` |
| Button | `.hz-btn` + `--primary`, `--secondary`, `--ghost` |
| Eyebrow | `.hz-eyebrow` + `--accent` |
| Inline | `.hz-kbd`, `.hz-code` |
| `TemplateFrame` chrome (5.1.0+) | `.hz-tf` + `__header`, `__eyebrow`, `__title`, `__description`, `__actions`, `__status`, `__body`, `__evidence`, `__evidence-link`, `__evidence-meta` |
| `Dashboard` template (5.1.0+) | `.hz-dashboard__content`, `__section`, `__section-title`, `__metrics`, `__metric`, `__label`, `__value`, `__detail`, `__table-wrap`, `__table`, `__list`, `__notice`, `__details`, `__empty` |
| `Form` template (5.1.0+) | `.hz-form` (root) + `__field`, `__description`, `__error`, `__submit` |

❌ **`hz-arch` (with `__chip`, `__dot`, `__label`) does not exist.** No CSS ships for it in this stylesheet — do not reference it for architecture diagrams or anything else; build a layout with `hz-card`/`hz-rail`/plain CSS instead.

A separate, differently-distributed package, `@huitzo/dashboard-primitives` (0.2.3), ships a shadcn/ui-style **copy-in** component registry (`hz-btn`, `hz-card`, `hz-chart`, `hz-form`, `hz-stat`, `hz-stream`, `hz-table` as real `.tsx`+`.module.css` source, not npm imports) — installed per-primitive into your `src/primitives/` via the CLI's `huitzo primitives` command group (`list`/`add`/`sync`/`diff`), with SHA-256-verified source. It is independent of the CSS-class primitives above; the two use overlapping names for related but distinct things (one is a plain class you add to a `<div>`, the other is a component file that lands in your repo).

## Dev harness and build contract

- `huitzo dashboard dev` (or `npm run dev`) serves `src/dev.tsx`, which builds a mock `HuitzoMountContext` and calls the real `mount()` — you get the exact lifecycle Hub uses, against fake data.
- `huitzo dashboard build` (or `npm run build`) runs Vite in **library mode**: entry `src/main.tsx`, format `es`, output `dist/main.js` — a single self-contained ESM module with React, the SDK, your app code, and CSS all bundled in (CSS is injected via `<style>` on import, not a separate file). Nothing is marked `external`; the dashboard carries its own React so it has zero version coupling with Hub.

## CSS isolation

Dashboards are mounted inside Hub's DOM, so:

- Scope every selector — CSS Modules (`*.module.css`) or plain CSS scoped under `.huitzo-dashboard` are both fine.
- ❌ Never write a bare global element selector (`button { … }`, `a { … }`, `:root { … }`) — it leaks into Hub and every other mounted dashboard.
- Rely on `hz-*` primitives and the token system before hand-rolling layout CSS.

## Error boundary

Wrap your root in an error boundary whose fallback offers a way back to Hub, since a dashboard-tree error does not propagate to Hub's own boundary (Hub only catches `mount`/`unmount`-level failures):

```typescript
function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  const { navigateToHub } = useHubNavigation();
  return (
    <div role="alert">
      <p>Something went wrong.</p>
      <button onClick={resetErrorBoundary}>Try again</button>
      <button onClick={navigateToHub}>Return to Hub</button>
    </div>
  );
}
```

## Security

- Never call `context.getToken()` outside your own request path, log it, or hand it to a third-party callback.
- Never use `dangerouslySetInnerHTML` without sanitizing (e.g. DOMPurify) — Hub renders your dashboard inline in its own page.
- Never read or write `window.location` or `document.body` — use `context.navigate*`/`context.emit` instead; the dashboard only owns its mount `container`.

## Anti-patterns

| Don't | Do instead |
|---|---|
| ❌ `color: #155DFC;` in component CSS | `color: var(--color-accent);` |
| ❌ `import { Button } from '@mui/material'` (or Ant/Chakra/shadcn) | `hz-btn` / `hz-card` primitives, or `@huitzo/dashboard-primitives` copy-in |
| ❌ `<div className="hz-arch__chip">` | `hz-arch` does not exist — use `hz-card`/`hz-rail` |
| ❌ `fetch('/api/v1/commands/...')` directly | `useCommand` / `client.commands.execute()` |
| ❌ Treating `useRealtime` as "needs a WebSocket" | It runs over Hub's per-mount event bus — no socket involved |
| ❌ Rendering without `<HuitzoProvider>` | Every hook throws outside it — wrap in `mount()` |
| ❌ Skipping the `.huitzo-dashboard` wrapper class | Tokens never resolve without it |
| ❌ A global `button { }` / `a { }` selector | Scope under `.huitzo-dashboard` or use CSS Modules |
| ❌ Assuming `useCommand.status` is 4-state (`idle\|loading\|success\|error`) | It is 5-state — `polling` exists for 202-receipt commands; check `isPolling` |
| ❌ `{ name: 'upload', label: 'File', type: 'file' }` in a `Form` | `FormFieldSpec` has no `file` type — build your own upload UI |

## Read more

- https://docs.huitzo.ai/docs/dashboards/sdk
- https://docs.huitzo.ai/docs/dashboards/overview
- https://docs.huitzo.ai/docs/dashboards/manifest
- https://docs.huitzo.ai/docs/dashboards/publishing
- https://docs.huitzo.ai/docs/cli/dashboards
