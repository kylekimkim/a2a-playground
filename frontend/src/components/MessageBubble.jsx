import ReactMarkdown from "react-markdown";

const styles = {
  wrapper: (role) => ({
    display: "flex",
    justifyContent: role === "user" ? "flex-end" : "flex-start",
    marginBottom: 8,
  }),
  bubble: (role, streaming) => ({
    maxWidth: "100%",
    padding: "16px 16px",
    borderRadius: role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
    background: role === "user" ? "#2563eb" : "#1e293b",
    color: role === "user" ? "#fff" : "#f8fafc",
    fontSize: 14,
    lineHeight: 1.6,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    boxShadow: "0 1px 2px rgba(0,0,0,0.08)",
    opacity: streaming ? 0.85 : 1,
    overflowX: "auto",
  }),
  cursor: {
    display: "inline-block",
    width: 8,
    height: 14,
    background: "#64748b",
    marginLeft: 2,
    borderRadius: 2,
    animation: "blink 1s step-end infinite",
    verticalAlign: "text-bottom",
  },
  label: (role) => ({
    fontSize: 12,
    color: "#94a3b8",
    marginBottom: 6,
    display: "flex",
    alignItems: "center",
    gap: 8,
    flexDirection: role === "user" ? "row-reverse" : "row",
  }),
  avatar: (role) => ({
    width: 24,
    height: 24,
    borderRadius: "50%",
    background: role === "user" ? "#2563eb" : "linear-gradient(135deg, #6366f1, #2563eb)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#fff",
    fontSize: 13,
  }),
};

export default function MessageBubble({ role, text, streaming = false, attachment = null }) {
  return (
    <div style={styles.wrapper(role)}>
      <div>
        <div style={styles.label(role)}>
          <div style={styles.avatar(role)}>
            {role === "user" ? "👤" : "🤖"}
          </div>
          <span style={{ fontWeight: 600 }}>{role === "user" ? "You" : "AI"}</span>
        </div>
        <div style={styles.bubble(role, streaming)}>
          {attachment && role === "user" && (
            <>
              <span style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                background: "rgba(255,255,255,0.15)",
                borderRadius: 6,
                padding: "2px 8px",
                fontSize: 12,
                marginRight: text ? 6 : 0,
                marginBottom: "6px",
                verticalAlign: "middle",
              }}>
                <span>📄</span>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 200 }}>
                  {attachment.filename}
                </span>
              </span>
              <br />
            </>
          )}
          {role === "agent" ? (
            <ReactMarkdown
              components={{
                p: ({ node, ...props }) => <p style={{ margin: 0, padding: 0, paddingBottom: 4 }} {...props} />,
                a: ({ node, href, children, ...props }) => {
                  if (href?.includes("/download/")) {
                    const filename = href.split("/download/")[1]?.replace(/['".,;)\]}\s]+$/, "") ?? "";
                    const ext = filename.split(".").pop()?.toUpperCase() ?? "";
                    return (
                      <a
                        href={href}
                        download={filename}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          background: "#1e3a5f",
                          border: "1px solid #2563eb",
                          color: "#60a5fa",
                          borderRadius: 8,
                          padding: "5px 12px",
                          fontSize: 13,
                          fontWeight: 600,
                          textDecoration: "none",
                          margin: "4px 0",
                          cursor: "pointer",
                        }}
                        {...props}
                      >
                        ⬇ {ext} 다운로드
                      </a>
                    );
                  }
                  return <a href={href} style={{ color: "#3b82f6" }} {...props}>{children}</a>;
                },
                ul: ({ node, ...props }) => <ul style={{ margin: "4px 0", paddingLeft: 24 }} {...props} />,
                ol: ({ node, ...props }) => <ol style={{ margin: "4px 0", paddingLeft: 24 }} {...props} />,
                li: ({ node, ...props }) => <li style={{ marginBottom: 4 }} {...props} />,
                code: ({ node, inline, ...props }) =>
                  inline ? (
                    <code style={{ background: "#334155", padding: "2px 4px", borderRadius: 4, fontFamily: "monospace", fontSize: 13 }} {...props} />
                  ) : (
                    <code style={{ display: "block", background: "#0f172a", padding: 8, borderRadius: 6, overflowX: "auto", fontFamily: "monospace", fontSize: 13, margin: "8px 0" }} {...props} />
                  ),
                blockquote: ({ node, children, ...props }) => {
                  const text = node?.children?.[0]?.children?.[0]?.value ?? "";
                  const isMcp = text.startsWith("🔌");
                  return (
                    <blockquote style={{
                      borderLeft: `3px solid ${isMcp ? "#10b981" : "#6366f1"}`,
                      paddingLeft: 12,
                      margin: "4px 0 8px 0",
                      color: isMcp ? "#6ee7b7" : "#94a3b8",
                      fontSize: 13,
                      fontStyle: "normal",
                      background: isMcp ? "rgba(16,185,129,0.07)" : "transparent",
                      borderRadius: isMcp ? "0 4px 4px 0" : 0,
                    }} {...props}>{children}</blockquote>
                  );
                },
              }}
            >
              {text}
            </ReactMarkdown>
          ) : (
            text
          )}
          {streaming && <span style={styles.cursor} />}
        </div>
      </div>
    </div>
  );
}
