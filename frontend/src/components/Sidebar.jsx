import { useState } from "react";

function relativeTime(ms) {
  const diff = Date.now() - ms;
  if (diff < 60_000) return "방금";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}분 전`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}시간 전`;
  return `${Math.floor(diff / 86_400_000)}일 전`;
}

function RoomItem({ room, active, onSwitch, onDelete }) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => onSwitch(room.id)}
      style={{
        padding: "10px 14px",
        borderRadius: 8,
        cursor: "pointer",
        background: active ? "#334155" : hovered ? "#253347" : "transparent",
        margin: "2px 8px",
        position: "relative",
        transition: "background 0.1s",
      }}
    >
      <div
        style={{
          fontSize: 13,
          color: "#f8fafc",
          fontWeight: active ? 600 : 400,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          paddingRight: 24,
        }}
      >
        {room.title}
      </div>
      <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
        {relativeTime(room.updated_at)}
      </div>

      {/* Delete button */}
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(room.id); }}
        style={{
          position: "absolute",
          right: 10,
          top: "50%",
          transform: "translateY(-50%)",
          opacity: hovered ? 1 : 0,
          background: "transparent",
          border: "none",
          color: "#ef4444",
          cursor: "pointer",
          fontSize: 15,
          padding: "2px 4px",
          lineHeight: 1,
          transition: "opacity 0.15s",
        }}
        title="채팅방 삭제"
      >
        🗑
      </button>
    </div>
  );
}

export default function Sidebar({ rooms, activeRoomId, onSwitch, onDelete, onCreate }) {
  return (
    <div
      style={{
        width: 260,
        minWidth: 260,
        height: "100dvh",
        background: "#1e293b",
        borderRight: "1px solid #334155",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <div style={{ padding: "16px 12px 12px", borderBottom: "1px solid #334155" }}>
        <div style={{ fontWeight: 700, fontSize: 15, color: "#f8fafc", marginBottom: 10 }}>
          💬 채팅
        </div>
        <button
          onClick={onCreate}
          style={{
            width: "100%",
            padding: "8px 0",
            borderRadius: 8,
            border: "none",
            background: "#2563eb",
            color: "#fff",
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          + 새 채팅
        </button>
      </div>

      {/* Room list */}
      <div style={{ flex: 1, overflowY: "auto", paddingTop: 6, paddingBottom: 6 }}>
        {rooms.length === 0 ? (
          <div style={{ textAlign: "center", color: "#64748b", fontSize: 13, marginTop: 24 }}>
            채팅방이 없습니다
          </div>
        ) : (
          rooms.map((room) => (
            <RoomItem
              key={room.id}
              room={room}
              active={room.id === activeRoomId}
              onSwitch={onSwitch}
              onDelete={onDelete}
            />
          ))
        )}
      </div>

      {/* Footer */}
      <div style={{ padding: "10px 14px", borderTop: "1px solid #334155" }}>
        <div style={{ fontSize: 11, color: "#475569" }}>GPT A2A Agent v1.0</div>
      </div>
    </div>
  );
}
