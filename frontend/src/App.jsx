import { useCallback, useState } from "react";
import { useRooms } from "./hooks/useRooms.js";
import { useA2AClient } from "./hooks/useA2AClient.js";
import { getRoomMessages } from "./api/roomsClient.js";
import Sidebar from "./components/Sidebar.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import InputBar from "./components/InputBar.jsx";
import AgentPanel from "./components/AgentPanel.jsx";

export default function App() {
  const [agentPanelOpen, setAgentPanelOpen] = useState(false);
  const { rooms, activeRoomId, handleCreate, handleDelete, switchRoom, renameRoom, touchRoom } =
    useRooms();

  const handleRoomTitled = useCallback(
    (roomId, title) => renameRoom(roomId, title),
    [renameRoom]
  );

  const handleMessageSaved = useCallback(
    () => touchRoom(activeRoomId),
    [touchRoom, activeRoomId]
  );

  const { messages, streamingText, isStreaming, error, send, abort, loadHistory } =
    useA2AClient({
      roomId: activeRoomId,
      onRoomTitled: handleRoomTitled,
      onMessageSaved: handleMessageSaved,
    });

  const handleSwitch = useCallback(
    async (roomId) => {
      switchRoom(roomId);
      try {
        const dbMessages = await getRoomMessages(roomId);
        loadHistory(dbMessages);
      } catch {
        loadHistory([]);
      }
    },
    [switchRoom, loadHistory]
  );

  const handleDeleteRoom = useCallback(
    async (roomId) => {
      const deletedId = await handleDelete(roomId);
      // If deleting the active room, load the next room's messages
      if (deletedId === activeRoomId) {
        const remaining = rooms.filter((r) => r.id !== deletedId);
        if (remaining.length > 0) {
          try {
            const dbMessages = await getRoomMessages(remaining[0].id);
            loadHistory(dbMessages);
          } catch {
            loadHistory([]);
          }
        } else {
          loadHistory([]);
        }
      }
    },
    [handleDelete, activeRoomId, rooms, loadHistory]
  );

  const handleNewChat = useCallback(async () => {
    await handleCreate();
    loadHistory([]);
  }, [handleCreate, loadHistory]);

  const handleSendMessage = useCallback(async (text, model, options = {}) => {
    let targetRoomId = activeRoomId;
    if (!targetRoomId) {
      targetRoomId = await handleCreate();
    }
    send(text, model, targetRoomId, options);
  }, [activeRoomId, handleCreate, send]);

  return (
    <>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f172a; color: #f8fafc; }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
      `}</style>

      <div style={{ display: "flex", height: "100dvh" }}>
        <Sidebar
          rooms={rooms}
          activeRoomId={activeRoomId}
          onSwitch={handleSwitch}
          onDelete={handleDeleteRoom}
          onCreate={handleNewChat}
        />


        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            minWidth: 0,
            background: "#0f172a",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "14px 20px",
              background: "#1e293b",
              borderBottom: "1px solid #334155",
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: "50%",
                background: "linear-gradient(135deg, #6366f1, #2563eb)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
                fontSize: 16,
                flexShrink: 0,
              }}
            >
              🤖
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 15, color: "#f8fafc" }}>
                {rooms.find((r) => r.id === activeRoomId)?.title ?? "GPT A2A Agent"}
              </div>
              <div style={{ fontSize: 12, color: "#94a3b8" }}>
                {isStreaming ? (
                  <span style={{ color: "#22c55e" }}>● 응답 중...</span>
                ) : (
                  <span>● 대기 중</span>
                )}
              </div>
            </div>
            {/* Agent registry toggle */}
            <button
              onClick={() => setAgentPanelOpen((v) => !v)}
              title="에이전트 레지스트리"
              style={{
                background: agentPanelOpen ? "#2563eb" : "transparent",
                border: "1px solid #334155",
                color: agentPanelOpen ? "#fff" : "#94a3b8",
                cursor: "pointer",
                fontSize: 13,
                padding: "6px 12px",
                borderRadius: 8,
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: 6,
                transition: "background 0.15s, color 0.15s",
              }}
            >
              🔌 에이전트
            </button>
          </div>

          {/* Error banner */}
          {error && (
            <div
              style={{
                padding: "10px 20px",
                background: "#450a0a",
                borderBottom: "1px solid #7f1d1d",
                color: "#fca5a5",
                fontSize: 13,
              }}
            >
              오류: {error}
            </div>
          )}

          {/* Chat area or empty state */}
          {activeRoomId ? (
            <ChatWindow
              messages={messages}
              streamingText={streamingText}
              isStreaming={isStreaming}
            />
          ) : (
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#475569",
                flexDirection: "column",
                gap: 8,
              }}
            >
              <div style={{ fontSize: 32 }}>💬</div>
              <div style={{ fontSize: 14 }}>새 채팅을 시작해보세요.</div>
            </div>
          )}

          <InputBar
            onSend={handleSendMessage}
            onAbort={abort}
            isStreaming={isStreaming}
          />
        </div>

        {agentPanelOpen && (
          <AgentPanel onClose={() => setAgentPanelOpen(false)} />
        )}
      </div>
    </>
  );
}
