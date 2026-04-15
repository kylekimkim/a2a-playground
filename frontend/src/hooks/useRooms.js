import { useState, useEffect, useCallback } from "react";
import { listRooms, createRoom, deleteRoom, updateRoomTitle } from "../api/roomsClient.js";

export function useRooms() {
  const [rooms, setRooms] = useState([]);
  const [activeRoomId, setActiveRoomId] = useState(null);

  const loadRooms = useCallback(async () => {
    try {
      const data = await listRooms();
      setRooms(data);
      return data;
    } catch {
      return [];
    }
  }, []);

  useEffect(() => {
    loadRooms().then((data) => {
      if (data.length > 0) setActiveRoomId(data[0].id);
    });
  }, [loadRooms]);

  const handleCreate = useCallback(async () => {
    const room = await createRoom();
    setRooms((prev) => [room, ...prev]);
    setActiveRoomId(room.id);
    return room.id;
  }, []);

  const handleDelete = useCallback(async (roomId) => {
    await deleteRoom(roomId);
    setRooms((prev) => {
      const next = prev.filter((r) => r.id !== roomId);
      // if deleted room was active, switch to first remaining
      if (roomId === activeRoomId) {
        setActiveRoomId(next[0]?.id ?? null);
      }
      return next;
    });
    return roomId;
  }, [activeRoomId]);

  const switchRoom = useCallback((roomId) => {
    setActiveRoomId(roomId);
  }, []);

  const renameRoom = useCallback(async (roomId, title) => {
    await updateRoomTitle(roomId, title).catch(() => {});
    setRooms((prev) =>
      prev.map((r) => (r.id === roomId ? { ...r, title } : r))
    );
  }, []);

  const touchRoom = useCallback((roomId) => {
    setRooms((prev) => {
      const room = prev.find((r) => r.id === roomId);
      if (!room) return prev;
      const rest = prev.filter((r) => r.id !== roomId);
      return [{ ...room, updated_at: Date.now() }, ...rest];
    });
  }, []);

  return { rooms, activeRoomId, handleCreate, handleDelete, switchRoom, renameRoom, touchRoom };
}
