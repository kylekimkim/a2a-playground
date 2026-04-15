import { useState, useRef } from "react";
import { uploadFile } from "../api/uploadClient.js";

const MODEL = "gpt-5.4-mini";

export default function InputBar({ onSend, onAbort, isStreaming, disabled }) {
  const [text, setText] = useState("");
  const [attachment, setAttachment] = useState(null); // { filename, path, uploading, error }
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  async function handleFileChange(e) {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;

    setAttachment({ filename: file.name, path: null, uploading: true, error: null });
    try {
      const { path } = await uploadFile(file);
      setAttachment({ filename: file.name, path, uploading: false, error: null });
    } catch (err) {
      setAttachment({ filename: file.name, path: null, uploading: false, error: err.message });
    }
  }

  function handleSend() {
    const hasText = text.trim();
    const hasFile = attachment?.path;
    if ((!hasText && !hasFile) || isStreaming || disabled) return;

    const displayText = text.trim();
    const fileHint = hasFile ? `파일 경로: ${attachment.path}` : "";
    let apiText = displayText;
    if (hasFile) {
      apiText = displayText
        ? `${displayText}\n\n${fileHint}`
        : `첨부된 파일의 내용을 분석해주세요.\n\n${fileHint}`;
    }

    onSend(apiText, MODEL, {
      displayText,
      attachment: hasFile ? { filename: attachment.filename } : null,
    });
    setText("");
    setAttachment(null);
    inputRef.current?.focus();
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const canSend = (text.trim() || attachment?.path) && !disabled;

  return (
    <div style={{ borderTop: "1px solid #334155", background: "#1e293b" }}>
      {/* 첨부 파일 뱃지 */}
      {attachment && (
        <div style={{ padding: "8px 16px 0" }}>
          <div style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            background: "#0f172a",
            border: "1px solid #334155",
            borderRadius: 8,
            padding: "4px 10px",
            fontSize: 13,
            color: attachment.error ? "#f87171" : "#94a3b8",
            maxWidth: "100%",
          }}>
            <span>{attachment.uploading ? "⏳" : attachment.error ? "❌" : "📄"}</span>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 300 }}>
              {attachment.uploading ? `업로드 중… ${attachment.filename}` : attachment.error ? attachment.error : attachment.filename}
            </span>
            {!attachment.uploading && (
              <button
                onClick={() => setAttachment(null)}
                style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", padding: 0, lineHeight: 1, fontSize: 14 }}
              >
                ✕
              </button>
            )}
          </div>
        </div>
      )}

      {/* 입력 행 */}
      <div style={{ padding: "12px 16px", display: "flex", gap: 8, alignItems: "flex-end" }}>
        {/* 파일 첨부 버튼 */}
        <input
          ref={fileInputRef}
          type="file"
          style={{ display: "none" }}
          accept=".pdf,.docx,.xlsx,.xls,.pptx,.txt,.md,.csv,.json,.xml,.html"
          onChange={handleFileChange}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isStreaming || disabled || attachment?.uploading}
          title="파일 첨부"
          style={{
            padding: "10px 12px",
            borderRadius: 12,
            border: "1px solid #334155",
            background: attachment?.path ? "#1e3a5f" : "#1e293b",
            color: attachment?.path ? "#60a5fa" : "#64748b",
            fontSize: 16,
            cursor: isStreaming || disabled || attachment?.uploading ? "not-allowed" : "pointer",
            flexShrink: 0,
            lineHeight: 1,
          }}
        >
          📎
        </button>

        <textarea
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isStreaming || disabled}
          placeholder={disabled ? "왼쪽 사이드바에서 새 채팅을 시작하세요" : "메시지를 입력하세요… (Enter로 전송)"}
          rows={1}
          style={{
            flex: 1,
            resize: "none",
            border: "1px solid #334155",
            borderRadius: 12,
            padding: "10px 14px",
            fontSize: 14,
            lineHeight: 1.5,
            outline: "none",
            fontFamily: "inherit",
            background: isStreaming || disabled ? "#0f172a" : "#1e293b",
            color: disabled ? "#64748b" : "#f8fafc",
            cursor: disabled ? "not-allowed" : "text",
          }}
        />

        {isStreaming ? (
          <button
            onClick={onAbort}
            style={{ padding: "10px 18px", borderRadius: 12, border: "none", background: "#ef4444", color: "#fff", fontSize: 14, cursor: "pointer", fontWeight: 600 }}
          >
            Stop
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!canSend}
            style={{
              padding: "10px 18px",
              borderRadius: 12,
              border: "none",
              background: canSend ? "#16a34a" : "#334155",
              color: canSend ? "#fff" : "#64748b",
              fontSize: 14,
              cursor: canSend ? "pointer" : "not-allowed",
              fontWeight: 600,
              transition: "all 0.15s",
            }}
          >
            Send
          </button>
        )}
      </div>
    </div>
  );
}
