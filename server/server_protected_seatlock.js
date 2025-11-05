
// server_protected_seatlock.js
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
const DEFAULT_TTL = parseInt(process.env.SEAT_LOCK_TTL || '120', 10);

function loadDB(){ return JSON.parse(fs.readFileSync(DB_FILE,'utf8') || '{}'); }
function saveDB(db){ fs.writeFileSync(DB_FILE, JSON.stringify(db,null,2), 'utf8'); }
function now(){ return Date.now(); }

(function migrate(){
  const db = loadDB();
  db.admins = db.admins || [];
  let changed=false;
  db.admins = db.admins.map(a=>{
    if (a.password_plain && !a.password){
      const out = { ...a, password: bcrypt.hashSync(a.password_plain,10) };
      delete out.password_plain; changed=true; return out;
    }
    return a;
  });
  if (!Array.isArray(db.seats)) { db.seats = []; changed=true; }
  if (changed) { saveDB(db); console.log('[migrate] applied'); }
})();

const app = express();
app.use(cors());
app.use(express.json());

app.get('/health', (req,res)=>res.json({ok:true, uptime:process.uptime()}));

app.post('/login', (req,res)=>{
  const {email, password} = req.body || {};
  if (!email || !password) return res.status(400).json({error:'Missing email or password'});
  const db = loadDB();
  const admin = (db.admins||[]).find(a=>a.email===email);
  if (!admin) return res.status(401).json({error:'Invalid credentials'});
  const ok = bcrypt.compareSync(password, admin.password || '');
  if (!ok) return res.status(401).json({error:'Invalid credentials'});
  const token = jwt.sign({sub:admin.id,email:admin.email,role:admin.role||'admin'}, JWT_SECRET, {expiresIn:'8h'});
  res.json({token});
});

function upsertSeat(db, seatId, fields){
  const idx = (db.seats||[]).findIndex(s=>String(s.id)===String(seatId));
  if (idx >= 0) { db.seats[idx] = { ...db.seats[idx], ...fields }; return db.seats[idx]; }
  const newSeat = { id: seatId, ...fields }; db.seats.push(newSeat); return newSeat;
}
function isLocked(seat){ return seat && seat.lockedBy && seat.holdUntil && (seat.holdUntil > now()); }
function remaining(seat){ return Math.max(0, Math.floor((seat.holdUntil - now())/1000)); }

app.get('/seats', (req,res)=>{
  const db = loadDB();
  let list = db.seats || [];
  const { roomId, id } = req.query || {};
  if (roomId) list = list.filter(s=>String(s.roomId)===String(roomId));
  if (id) list = list.filter(s=>String(s.id)===String(id));
  list = list.map(s=> isLocked(s) ? s : ({...s, lockedBy:null, holdUntil:null}) );
  res.json(list);
});

app.post('/seats/lock', (req,res)=>{
  const { seatId, roomId, userId, ttlSeconds } = req.body || {};
  if (!seatId || !userId) return res.status(400).json({error:'seatId and userId required'});
  const db = loadDB();
  const seat = (db.seats||[]).find(s=>String(s.id)===String(seatId));
  if (seat && isLocked(seat) && String(seat.lockedBy)!==String(userId)) {
    return res.status(409).json({error:'Seat already locked', by:seat.lockedBy, remaining: remaining(seat)});
  }
  const ttl = Math.max(10, parseInt(ttlSeconds||DEFAULT_TTL,10));
  const updated = upsertSeat(db, seatId, {
    roomId: roomId ?? (seat && seat.roomId),
    lockedBy: String(userId),
    lockedAt: now(),
    holdUntil: now() + ttl*1000,
    status: 'locked'
  });
  saveDB(db);
  res.json(updated);
});

app.post('/seats/refresh', (req,res)=>{
  const { seatId, userId, ttlSeconds } = req.body || {};
  if (!seatId || !userId) return res.status(400).json({error:'seatId and userId required'});
  const db = loadDB();
  const seat = (db.seats||[]).find(s=>String(s.id)===String(seatId));
  if (!seat || !isLocked(seat) || String(seat.lockedBy)!==String(userId)) {
    return res.status(409).json({error:'Not lock owner (or lock expired)'});
  }
  const ttl = Math.max(10, parseInt(ttlSeconds||DEFAULT_TTL,10));
  seat.holdUntil = now() + ttl*1000;
  saveDB(db);
  res.json(seat);
});

app.post('/seats/unlock', (req,res)=>{
  const { seatId, userId } = req.body || {};
  if (!seatId || !userId) return res.status(400).json({error:'seatId and userId required'});
  const db = loadDB();
  const seat = (db.seats||[]).find(s=>String(s.id)===String(seatId));
  if (!seat) return res.json({ok:true});
  if (seat.lockedBy && String(seat.lockedBy)!==String(userId) && isLocked(seat)) {
    return res.status(403).json({error:'Cannot unlock others lock'});
  }
  seat.lockedBy = null; seat.holdUntil = null; seat.status = 'free';
  saveDB(db);
  res.json({ok:true});
});

const PUBLIC_RULES = [
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
  ['GET',   /^\/seats(\/.*)?$/],
  ['POST',  /^\/seats\/(lock|unlock|refresh)$/],
];

function isPublic(req){ return PUBLIC_RULES.some(([m, rx]) => m===req.method && rx.test(req.path)); }

function authGuard(req,res,next){
  if (req.path === '/login' || req.path === '/health') return next();
  if (isPublic(req)) return next();
  const header = req.headers['authorization'] || '';
  const [scheme, token] = header.split(' ');
  if (scheme !== 'Bearer' || !token) return res.status(401).json({ error:'Missing or invalid Authorization header' });
  try {
    const p = jwt.verify(token, JWT_SECRET);
    if (p.role !== 'admin') return res.status(403).json({ error:'Admin role required' });
    next();
  } catch(e){ return res.status(401).json({ error:'Invalid or expired token' }); }
}

const router = jsonServer.router(DB_FILE);
const defaults = jsonServer.defaults();
app.use(authGuard, defaults, router);

app.listen(PORT, ()=>{
  console.log(`[seatlock] http://localhost:${PORT}`);
  console.log(`DB file: ${DB_FILE}`);
  console.log(`Seat lock TTL default: ${DEFAULT_TTL}s`);
});
