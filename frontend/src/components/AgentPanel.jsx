import { useState } from "react";
import { useAgentRegistry } from "../hooks/useAgentRegistry.js";

function AgentDetailModal({ agent, onClose }) {
  const card = agent.card;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#1e293b",
          border: "1px solid #334155",
          borderRadius: 12,
          padding: 24,
          width: 440,
          maxWidth: "90vw",
          maxHeight: "80vh",
          overflowY: "auto",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: agent.online ? "#22c55e" : "#ef4444",
                flexShrink: 0,
                marginTop: 2,
              }}
            />
            <div>
              <div style={{ fontWeight: 700, fontSize: 16, color: "#f8fafc" }}>
                {card?.name ?? agent.url}
              </div>
              <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{agent.url}</div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              fontSize: 18,
              cursor: "pointer",
              padding: "0 4px",
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>

        {/* Status badge */}
        <div style={{ marginBottom: 16 }}>
          <span
            style={{
              display: "inline-block",
              padding: "3px 10px",
              borderRadius: 999,
              fontSize: 12,
              fontWeight: 600,
              background: agent.online ? "#14532d" : "#450a0a",
              color: agent.online ? "#4ade80" : "#f87171",
            }}
          >
            {agent.online ? "온라인" : "오프라인"}
          </span>
        </div>

        {!card ? (
          <div style={{ color: "#64748b", fontSize: 13 }}>에이전트 카드 정보를 가져올 수 없습니다.</div>
        ) : (
          <>
            {/* Description */}
            {card.description && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: 4 }}>
                  설명
                </div>
                <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6 }}>{card.description}</div>
              </div>
            )}

            {/* Version & Provider */}
            <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
              {card.version && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: 2 }}>버전</div>
                  <div style={{ fontSize: 13, color: "#cbd5e1" }}>{card.version}</div>
                </div>
              )}
              {card.provider?.organization && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: 2 }}>제공자</div>
                  <div style={{ fontSize: 13, color: "#cbd5e1" }}>{card.provider.organization}</div>
                </div>
              )}
              {card.provider?.model && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: 2 }}>모델</div>
                  <div style={{ fontSize: 13, color: "#cbd5e1" }}>{card.provider.model}</div>
                </div>
              )}
            </div>

            {/* Skills */}
            {card.skills?.length > 0 && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: 8 }}>
                  스킬 ({card.skills.length})
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {card.skills.map((s, i) => (
                    <div
                      key={i}
                      style={{
                        background: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: 8,
                        padding: "10px 12px",
                      }}
                    >
                      <div style={{ fontWeight: 600, fontSize: 13, color: "#a5b4fc", marginBottom: 4 }}>
                        {s.name}
                      </div>
                      {s.description && (
                        <div style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.5 }}>{s.description}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function AgentItem({ agent, onDelete, onDetail }) {
  const [hovered, setHovered] = useState(false);
  const card = agent.card;

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: "10px 12px",
        borderRadius: 8,
        background: hovered ? "#253347" : "transparent",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        gap: 10,
        transition: "background 0.1s",
      }}
      onClick={() => onDetail(agent)}
    >
      {/* Status dot */}
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          flexShrink: 0,
          background: agent.online ? "#22c55e" : "#ef4444",
          boxShadow: agent.online ? "0 0 6px #22c55e88" : "none",
        }}
      />

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "#f8fafc",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {card?.name ?? agent.url}
        </div>
        <div
          style={{
            fontSize: 11,
            color: "#64748b",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            marginTop: 1,
          }}
        >
          {agent.url}
        </div>
      </div>

      {/* Delete button */}
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(agent.url); }}
        title="에이전트 삭제"
        style={{
          opacity: hovered ? 1 : 0,
          background: "transparent",
          border: "none",
          color: "#ef4444",
          cursor: "pointer",
          fontSize: 14,
          padding: "2px 4px",
          lineHeight: 1,
          flexShrink: 0,
          transition: "opacity 0.15s",
        }}
      >
        ✕
      </button>
    </div>
  );
}

export default function AgentPanel({ onClose }) {
  const { agents, loading, error, refresh, add, remove } = useAgentRegistry();
  const [addUrl, setAddUrl] = useState("");
  const [addError, setAddError] = useState(null);
  const [addLoading, setAddLoading] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);

  const onlineCount = agents.filter((a) => a.online).length;

  async function handleAdd(e) {
    e.preventDefault();
    const url = addUrl.trim();
    if (!url) return;
    setAddLoading(true);
    setAddError(null);
    const err = await add(url);
    setAddLoading(false);
    if (err) {
      setAddError(err);
    } else {
      setAddUrl("");
    }
  }

  async function handleDelete(url) {
    const err = await remove(url);
    if (err) alert(err);
  }

  return (
    <>
      <div
        style={{
          width: 280,
          minWidth: 280,
          height: "100dvh",
          background: "#1e293b",
          borderLeft: "1px solid #334155",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "16px 14px 12px",
            borderBottom: "1px solid #334155",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: "#f8fafc" }}>
              🔌 에이전트 레지스트리
            </div>
            <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>
              {onlineCount}/{agents.length} 온라인
            </div>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button
              onClick={refresh}
              title="새로고침"
              style={{
                background: "transparent",
                border: "1px solid #334155",
                color: "#94a3b8",
                cursor: "pointer",
                fontSize: 13,
                padding: "4px 8px",
                borderRadius: 6,
                lineHeight: 1,
              }}
            >
              ↺
            </button>
            <button
              onClick={onClose}
              title="닫기"
              style={{
                background: "transparent",
                border: "1px solid #334155",
                color: "#94a3b8",
                cursor: "pointer",
                fontSize: 13,
                padding: "4px 8px",
                borderRadius: 6,
                lineHeight: 1,
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Agent list */}
        <div style={{ flex: 1, overflowY: "auto", padding: "8px 4px" }}>
          {error && (
            <div style={{ padding: "8px 12px", color: "#f87171", fontSize: 12 }}>
              오류: {error}
            </div>
          )}
          {agents.length === 0 && !error ? (
            <div style={{ textAlign: "center", color: "#475569", fontSize: 13, marginTop: 24 }}>
              등록된 에이전트가 없습니다
            </div>
          ) : (
            agents.map((agent) => (
              <AgentItem
                key={agent.url}
                agent={agent}
                onDelete={handleDelete}
                onDetail={setSelectedAgent}
              />
            ))
          )}
        </div>

        {/* Add agent form */}
        <div style={{ padding: "12px 12px 14px", borderTop: "1px solid #334155" }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 6 }}>
            에이전트 추가
          </div>
          <form onSubmit={handleAdd} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <input
              type="text"
              value={addUrl}
              onChange={(e) => { setAddUrl(e.target.value); setAddError(null); }}
              placeholder="http://127.0.0.1:9004"
              style={{
                background: "#0f172a",
                border: `1px solid ${addError ? "#ef4444" : "#334155"}`,
                borderRadius: 6,
                color: "#f8fafc",
                fontSize: 12,
                padding: "7px 10px",
                outline: "none",
              }}
            />
            {addError && (
              <div style={{ fontSize: 11, color: "#f87171" }}>{addError}</div>
            )}
            <button
              type="submit"
              disabled={addLoading || !addUrl.trim()}
              style={{
                padding: "7px 0",
                borderRadius: 6,
                border: "none",
                background: addUrl.trim() ? "#2563eb" : "#1e3a5f",
                color: addUrl.trim() ? "#fff" : "#64748b",
                fontSize: 13,
                fontWeight: 600,
                cursor: addUrl.trim() ? "pointer" : "default",
                transition: "background 0.1s",
              }}
            >
              {addLoading ? "추가 중..." : "+ 추가"}
            </button>
          </form>
        </div>
      </div>

      {/* Detail modal */}
      {selectedAgent && (
        <AgentDetailModal agent={selectedAgent} onClose={() => setSelectedAgent(null)} />
      )}
    </>
  );
}
