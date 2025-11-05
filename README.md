# Smart Seat – Ready-to-Run Bundle

Generated: 2025-11-03T03:39:03

This bundle contains everything you need to run the demo backend (Express + json-server),
JWT-protected admin pages, a user booking UI, and the optional seat-lock server.

## Folder Layout

- `server/`
  - `server_protected_public.js` — backend with public whitelist (recommended for user UI)
  - `server_protected_seatlock.js` — backend with seat-lock service enabled (admin-protected endpoints)
  - `server_protected.js` — base protected server (if present)
  - `reset_admin.js` — utility to reset admin credentials
  - `seatLockClient.js` — client helper for seat lock API (used by website_user_seatlock.html)
- `public/`
  - `admin_login*.html`, `admin_dashboard*.html` — admin pages (debug variants included)
  - `website_user_connected.html` — user booking UI (talks to /users, /rooms, /reservations)
  - `website_user_seatlock.html` — user UI that demonstrates live seat-locking
- `data/`
  - `db.secure.json` — primary database
  - `db.integrated.json` — optional sample
- `scripts/`
  - `StartServer.bat` — one-click start (edit if needed)
  - `ResetAdmin.bat` — reset default admin to admin@example.com / Admin@123
- `package.json`, `package-lock.json`

## Quick Start (Windows CMD)

1. Install dependencies (once):
   ```bat
   cd smart-seat-bundle
   npm install
   ```

2. Start the backend (public whitelist):
   ```bat
   set JWT_SECRET=change-me-in-prod
   set DB_FILE=%cd%\data\db.secure.json
   node server\server_protected_public.js
   ```
   You should see:
   ```
   [public] http://localhost:3000
   ```

3. Open a browser (Chrome recommended) and load the user UI:
   - `public/website_user_connected.html` (double-click to open)
   - Login with any email → reserve → pick a seat → confirm.

### Admin Pages

- Login:
  - Open `public/admin_login_debug.html`
  - Email: `admin@example.com`
  - Password: `Admin@123` (use `scripts/ResetAdmin.bat` if you need to reset)

- Dashboard:
  - `public/admin_dashboard_debug.html` (auto-uses the token from login page)

### Health Check

Visit: `http://localhost:3000/health` → should return `{"ok":true,...}`

### Seat Lock Server (optional)

- Start:
  ```bat
  set JWT_SECRET=change-me-in-prod
  set DB_FILE=%cd%\data\db.secure.json
  node server\server_protected_seatlock.js
  ```

- Demo page:
  - Open `public/website_user_seatlock.html`

### Notes

- If your browser shows **Failed to fetch**, ensure the backend is running and accessible on `http://localhost:3000`.
- If you see **Missing or invalid Authorization header** while using admin endpoints, login first to obtain a JWT (admin pages do this automatically).
- You can also serve the `public/` folder via a local static server if needed:
  ```bat
  npx serve public
  ```

---

Missing files in this bundle (not found when generating): []
