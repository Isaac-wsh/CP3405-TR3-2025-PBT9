
# Admin-only Login for the Database (JSON Server + JWT)

This adds a protected gateway in front of `json-server` so **only admins** can log in and access the database UI or API.

## What you got
- `server_protected.js` — Express + json-server + JWT auth. Protects all endpoints except `/login` and `/health`.
- `db.secure.json` — Database file with an initial admin:
  - email: `admin@example.com`
  - password: `Admin@123` (stored as `password_plain` initially; automatically hashed at first run)
- `admin_login.html` — Minimal login page that obtains a JWT.
- `admin_dashboard.html` — Simple CRUD dashboard for any collection, using the JWT.

## Install & Run
```bash
# 1) Install deps
npm i express json-server bcryptjs jsonwebtoken cors

# 2) Start the protected server (default port 3000)
node server_protected.js
# Or set env vars:
#   PORT=3000 JWT_SECRET="your-strong-secret" DB_FILE="./db.secure.json" node server_protected.js
```

The server will hash any `password_plain` in `admins` on first run and remove it from the DB file.

## Using the Admin UI
1. Open `admin_login.html` in your browser.
2. Ensure `AUTH_API` points to your server (defaults to `http://localhost:3000`). You can set it in DevTools:
   ```js
   localStorage.setItem('AUTH_API','http://localhost:3000')
   ```
3. Sign in with `admin@example.com` / `Admin@123`.
4. You’ll be redirected to `admin_dashboard.html` where you can browse and mutate collections.

## Protecting Production
- Change `JWT_SECRET` via environment variables.
- Change the admin password: after first run, update the admin entry using the dashboard or by editing the DB (set a new `password_plain`, restart server to re-hash).
- Put this behind HTTPS if exposed beyond localhost.
- Consider backing up `db.secure.json` routinely.

## How it Works
- `POST /login` validates admin credentials and issues a JWT.
- All other routes require `Authorization: Bearer <token>` and role `admin`.
- `json-server` handles RESTful CRUD for all collections in `db.secure.json`, behind the auth middleware.
```

