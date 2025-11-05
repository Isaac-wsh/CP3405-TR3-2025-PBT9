
// server_protected.js
// An auth gateway in front of json-server.
// Usage:
//   npm i express json-server bcryptjs jsonwebtoken cors
//   node server_protected.js

const fs = require('fs');
const path = require('path');
const express = require('express');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const cors = require('cors');
const jsonServer = require('json-server');

const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'change-me-in-production';
const DB_FILE = process.env.DB_FILE || path.join(__dirname, 'db.secure.json');

// Load DB
function loadDB() {
  const raw = fs.readFileSync(DB_FILE, 'utf8');
  return JSON.parse(raw);
}
function saveDB(db) {
  fs.writeFileSync(DB_FILE, JSON.stringify(db, null, 2), 'utf8');
}

// One-time migration: hash any `password_plain` fields
(function migratePasswords() {
  const db = loadDB();
  if (Array.isArray(db.admins)) {
    let changed = false;
    db.admins = db.admins.map(a => {
      if (a.password_plain && !a.password) {
        const hash = bcrypt.hashSync(a.password_plain, 10);
        const out = { ...a };
        out.password = hash;
        delete out.password_plain;
        changed = true;
        return out;
      }
      return a;
    });
    if (changed) {
      saveDB(db);
      console.log('[migrate] Admin plaintext passwords hashed and removed.');
    }
  }
})();

const app = express();
app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ ok: true, uptime: process.uptime() });
});

// Login route
app.post('/login', (req, res) => {
  const { email, password } = req.body || {};
  if (!email || !password) {
    return res.status(400).json({ error: 'Missing email or password' });
  }
  const db = loadDB();
  const admin = (db.admins || []).find(a => a.email === email);
  if (!admin) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }
  const ok = bcrypt.compareSync(password, admin.password || '');
  if (!ok) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }
  const token = jwt.sign(
    { sub: admin.id, email: admin.email, role: admin.role || 'admin' },
    JWT_SECRET,
    { expiresIn: '8h' }
  );
  res.json({ token });
});

// Auth middleware for everything except /login and /health
function authGuard(req, res, next) {
  if (req.path === '/login' || req.path === '/health') return next();
  const header = req.headers['authorization'] || '';
  const [scheme, token] = header.split(' ');
  if (scheme !== 'Bearer' || !token) {
    return res.status(401).json({ error: 'Missing or invalid Authorization header' });
  }
  try {
    const payload = jwt.verify(token, JWT_SECRET);
    req.user = payload;
    // optional: enforce role
    if (payload.role !== 'admin') {
      return res.status(403).json({ error: 'Admin role required' });
    }
    next();
  } catch (e) {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

// Mount json-server behind auth
const router = jsonServer.router(DB_FILE);
const middlewares = jsonServer.defaults();

app.use(authGuard, middlewares, router);

app.listen(PORT, () => {
  console.log(`[auth-json-server] listening on http://localhost:${PORT}`);
  console.log(`DB file: ${DB_FILE}`);
});
