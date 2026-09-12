---
name: dashboard-dev
description: Start the local dashboard dev server (Vite + a mock HuitzoMountContext) and point it at a running backend or sandbox.
disable-model-invocation: true
---

# /dashboard-dev

Start local development for a dashboard.

## Steps

1. **Check prerequisites**:
   - `package.json` and `huitzo-dashboard.yaml` exist.
   - `node_modules/` exists (if not, run `npm install` first).
   - `src/dev.tsx` exists — the dev-only entry that builds a mock
     `HuitzoMountContext` and calls the real exported `mount()`.

2. **Start the server** — prefer the CLI when `huitzo` is on PATH, otherwise
   the npm script directly:

   ```bash
   huitzo dashboard dev
   # equivalent to:
   npm run dev
   ```

   Both wrap the same Vite dev server.

3. **What you get:**
   - Served at `http://localhost:3000` with hot module replacement.
   - `index.html` loads `src/dev.tsx`, which imports `mount()` from
     `src/main.tsx` and calls it with the mock context — the exact
     `mount`/`unmount` lifecycle Hub uses, against fake data.
   - A simulated Hub header renders above the dashboard, including a
     **theme toggle** (dark/light) that flips `data-theme` on
     `<html>` — use it to verify both themes per `dashboard-design.md`.
   - `/api/*` requests are proxied to `http://localhost:8080` by default
     (Vite's `server.proxy` config), so relative API calls behave like they
     would once mounted, without CORS friction.

4. **Point dev at a running sandbox or a different backend** — the dev
   server has no CLI flag for this; edit the proxy target directly in
   `vite.config.ts`:

   ```typescript
   server: {
     port: 3000,
     proxy: { '/api': { target: 'http://<sandbox-host>:<port>', changeOrigin: true } },
   },
   ```

   If the sandbox needs a different `apiUrl` in the mock context itself
   (rather than only proxying), also update `apiUrl` in `src/dev.tsx`'s mock
   `HuitzoMountContext`. Restart `npm run dev` after either change — Vite
   does not hot-reload its own config.

5. **Remind the user:**
   - This is a simulation with mock data — the real JWT, real navigation,
     and real Hub-emitted events only exist once published and loaded by Hub.
   - Update `src/dev.tsx`'s mock context whenever `HuitzoMountContext` gains
     a field your dashboard reads, so dev mode doesn't silently diverge from
     production (see `hub-contract.md` for the current field list).
