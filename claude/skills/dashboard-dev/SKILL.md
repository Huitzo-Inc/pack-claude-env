---
description: Start the Vite development server for dashboard development
disable-model-invocation: true
---

# /dashboard-dev

Start the local development server for dashboard development.

## Steps

1. **Check prerequisites**:
   - `package.json` exists
   - `node_modules/` exists (if not, suggest `npm install`)
   - `huitzo-dashboard.yaml` exists
   - `src/dev.tsx` exists (the development entry point)

2. **Start the dev server**:
   ```bash
   npm run dev
   ```

3. **Report** the local URL (typically `http://localhost:5173`) and remind the user:
   - The dev server uses `src/dev.tsx` which provides a mocked `HuitzoContext`
   - Changes to components will hot-reload
   - This simulates how Hub loads your dashboard but with mock data
   - To test with real Hub, you'll need to build and deploy
