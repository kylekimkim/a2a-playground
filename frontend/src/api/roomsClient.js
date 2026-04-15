const BASE = "/rooms";

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 204) return null;
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export const listRooms = () => req("");
export const createRoom = () => req("", { method: "POST", body: JSON.stringify({}) });
export const deleteRoom = (id) => req(`/${id}`, { method: "DELETE" });
export const getRoomMessages = (id) => req(`/${id}/messages`);
export const updateRoomTitle = (id, title) =>
  req(`/${id}`, { method: "PATCH", body: JSON.stringify({ title }) });
