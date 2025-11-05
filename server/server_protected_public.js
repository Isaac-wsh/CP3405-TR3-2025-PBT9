
// server_protected_public.js
// Auth gateway for json-server with a public whitelist for user frontend.
const fs = require('fs');
const path = require('path');
const express = require('express');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const cors = require('cors');
const jsonServer = require('json-server');

const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'change-me-in-prod';
const DB_FILE = process.env.DB_FILE || path.join(__dirname, 'db.integrated.json');

function loadDB(){ return JSON.parse(fs.readFileSync(DB_FILE,'utf8')); }
function saveDB(db){ fs.writeFileSync(DB_FILE, JSON.stringify(db,null,2), 'utf8'); }

// one-time migrate: hash password_plain
(function migrate(){
  const db = loadDB();
  if (Array.isArray(db.admins)) {
    let changed=false;
    db.admins = db.admins.map(a => {
      if (a.password_plain && !a.password) {
        const out = { ...a, password: bcrypt.hashSync(a.password_plain, 10) };
        delete out.password_plain; changed=true; return out;
      }
      return a;
    });
    if (changed) { saveDB(db); console.log('[migrate] admin passwords hashed.'); }
  }
})();

const app = express();
app.use(cors());
app.use(express.json());

// health
app.get('/health', (req,res) => res.json({ ok:true, uptime: process.uptime() }));

// login -> JWT
app.post('/login', (req,res) => {
  const { email, password } = req.body || {};
  if (!email || !password) return res.status(400).json({ error: 'Missing email or password' });
  const db = loadDB();
  const admin = (db.admins||[]).find(a=>a.email===email);
  if (!admin) return res.status(401).json({ error: 'Invalid credentials' });
  const ok = bcrypt.compareSync(password, admin.password || '');
  if (!ok) return res.status(401).json({ error: 'Invalid credentials' });
  const token = jwt.sign({ sub: admin.id, email: admin.email, role: admin.role || 'admin' }, JWT_SECRET, { expiresIn:'8h' });
  res.json({ token });
});

// ---- Public whitelist for user frontend ----
const PUBLIC_RULES = [
  // method, path (regex)
  ['GET',   /^\/buildings(\/.*)?$/],
  ['GET',   /^\/rooms(\/.*)?$/],
  ['GET',   /^\/users(\/.*)?$/],
  ['POST',  /^\/users$/],
  ['PATCH', /^\/users\/[^/]+$/],
  ['GET',   /^\/reservations(\/.*)?$/],
  ['POST',  /^\/reservations$/],
  ['PATCH', /^\/reservations\/[^/]+$/],
  ['GET',   /^\/reservationEvents(\/.*)?$/],
  ['POST',  /^\/reservationEvents$/],
];

function isPublic(req){
  return PUBLIC_RULES.some(([m, rx]) => m===req.method && rx.test(req.path));
}

// ---- Auth guard: allow public, protect others ----
function authGuard(req, res, next){
  if (req.path === '/login' || req.path === '/health') return next();
  if (isPublic(req)) return next();
  const header = req.headers['authorization'] || '';
  const [scheme, token] = header.split(' ');
  if (scheme !== 'Bearer' || !token) return res.status(401).json({ error:'Missing or invalid Authorization header' });
  try {
    const p = jwt.verify(token, JWT_SECRET);
    if (p.role !== 'admin') return res.status(403).json({ error: 'Admin role required' });
    next();
  } catch(e){ return res.status(401).json({ error:'Invalid or expired token' }); }
}

const router = jsonServer.router(DB_FILE);
const defaults = jsonServer.defaults();

app.use(authGuard, defaults, router);

app.listen(PORT, ()=>{
  console.log(`[auth-json-server+public] http://localhost:${PORT}`);
  console.log(`DB file: ${DB_FILE}`);
  console.log(`[public] open endpoints include GET rooms/buildings/users/reservations, POST/PATCH reservations, etc.`);
});
