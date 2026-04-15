import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble.jsx";

export default function ChatWindow({ messages, streamingText, isStreaming }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "16px 20px",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {messages.length === 0 && !isStreaming && (
        <div
          style={{
            margin: "auto",
            textAlign: "center",
            color: "#64748b",
            fontSize: 14,
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 8 }}>💬</div>
          <div>AI에게 메시지를 보내보세요.</div>
        </div>
      )}

      {messages.map((msg) => (
        <MessageBubble key={msg.id} role={msg.role} text={msg.text} attachment={msg.attachment} />
      ))}

      {isStreaming && !streamingText && (
        <MessageBubble role="agent" text="AI가 생각중입니다..." streaming />
      )}

      {isStreaming && streamingText && (
        <MessageBubble role="agent" text={streamingText} streaming />
      )}

      <div ref={bottomRef} />
    </div>
  );
}
