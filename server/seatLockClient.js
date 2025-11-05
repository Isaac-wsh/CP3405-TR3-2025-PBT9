
// seatLockClient.js
export function seatAPI() {
  const api = (localStorage.getItem('AUTH_API') || 'http://localhost:3000').replace(/\/+$/,'');
  return api;
}
export async function getSeatStates({roomId}={}) {
  const api = seatAPI();
  const q = roomId ? `?roomId=${encodeURIComponent(roomId)}` : '';
  const r = await fetch(`${api}/seats${q}`);
  return await r.json();
}
export async function lockSeat({seatId, roomId, userId, ttlSeconds=120}) {
  const api = seatAPI();
  const r = await fetch(`${api}/seats/lock`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({seatId, roomId, userId, ttlSeconds})
  });
  if (r.status === 409) {
    const j = await r.json();
    throw Object.assign(new Error('Seat already locked'), {code:409, detail:j});
  }
  if (!r.ok) throw new Error('Lock failed: '+r.status);
  return await r.json();
}
export async function refreshLock({seatId, userId, ttlSeconds=120}) {
  const api = seatAPI();
  const r = await fetch(`${api}/seats/refresh`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({seatId, userId, ttlSeconds})
  });
  if (!r.ok) throw new Error('Refresh failed: '+r.status);
  return await r.json();
}
export async function unlockSeat({seatId, userId}) {
  const api = seatAPI();
  const r = await fetch(`${api}/seats/unlock`, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({seatId, userId})
  });
  if (!r.ok) throw new Error('Unlock failed: '+r.status);
  return await r.json();
}
