// reset_admin.js
// Usage: node reset_admin.js "C:\path\to\db.secure.json"
const fs = require('fs');
const path = require('path');

const file = process.argv[2] || process.env.DB_FILE;
if (!file) {
  console.error('Provide path to db.secure.json, e.g.: node reset_admin.js C:\\Users\\you\\Desktop\\1\\db.secure.json');
  process.exit(1);
}
const p = path.resolve(file);
const raw = fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '{}';
const db = raw.trim() ? JSON.parse(raw) : {};

db.admins = [
  { id: 1, email: 'admin@example.com', password_plain: 'Admin@123', role: 'admin' }
];
db.users = db.users || [];
db.reservations = db.reservations || [];
db.reservationEvents = db.reservationEvents || [];
db.buildings = db.buildings || [];
db.rooms = db.rooms || [];
db.seats = db.seats || [];

fs.writeFileSync(p, JSON.stringify(db, null, 2), 'utf8');
console.log('[reset] Admin restored to admin@example.com / Admin@123 at', p);