const RPC_URL = "/chat";
let _rpcId = 1;

function nextId() {
  return _rpcId++;
}

/**
 * tasks/sendSubscribe — streaming.
 * Calls onDelta(text) for each token, onDone() when complete, onError(err) on failure.
 * Returns an AbortController so the caller can cancel.
 */
export function subscribeTask(text, { onDelta, onDone, onError, sessionId = null, model = null }) {
  const controller = new AbortController();
  const body = {
    jsonrpc: "2.0",
    id: nextId(),
    method: "message/stream",
    params: {
      session_id: sessionId,
      message: {
        role: "user",
        parts: [{ type: "text", text }],
      },
      ...(model ? { metadata: { model } } : {}),
    },
  };

  (async () => {
    let completed = false;
    try {
      const res = await fetch(RPC_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep incomplete last line

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          let event;
          try {
            event = JSON.parse(raw);
          } catch {
            continue;
          }

          if (event.type === "task_artifact_update") {
            const parts = event.artifact?.parts ?? [];
            for (const part of parts) {
              if (part.type === "text" && part.text) {
                onDelta(part.text);
              }
            }
          }

          if (event.type === "error") {
            completed = true;
            onError(new Error(event.message || "서버 오류가 발생했습니다."));
          }

          if (event.type === "task_status_update" && event.final) {
            completed = true;
            onDone();
          }
        }
      }

      // 스트림이 final 이벤트 없이 종료된 경우 fallback
      if (!completed) onDone();
    } catch (err) {
      if (err.name !== "AbortError") onError(err);
    }
  })();

  return controller;
}
