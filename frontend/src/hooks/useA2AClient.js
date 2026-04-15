import { useState, useRef, useCallback, useEffect } from "react";
import { subscribeTask } from "../api/a2aClient.js";

export function useA2AClient({ roomId, onRoomTitled, onMessageSaved }) {
  const [messages, setMessages] = useState([]);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);
  const isFirstMessage = useRef(true);

  // Reset is now managed directly by loadHistory when switching rooms.
  const loadHistory = useCallback((dbMessages) => {
    abortRef.current?.abort();
    const mapped = dbMessages.map((m) => ({
      id: m.id,
      role: m.role,
      text: m.content,
    }));
    setMessages(mapped);
    setStreamingText("");
    setIsStreaming(false);
    setError(null);
    isFirstMessage.current = mapped.length === 0;
  }, []);

  const appendMessage = useCallback((role, text, attachment = null) => {
    setMessages((prev) => [...prev, { id: Date.now() + Math.random(), role, text, attachment }]);
  }, []);

  const send = useCallback(
    (text, model = null, overrideRoomId = null, options = {}) => {
      const targetRoomId = overrideRoomId || roomId;
      if (!text.trim() || !targetRoomId) return;
      const { displayText, attachment } = options;
      setError(null);
      appendMessage("user", displayText ?? text, attachment ?? null);

      // Auto-title room from first message
      if (isFirstMessage.current) {
        isFirstMessage.current = false;
        onRoomTitled?.(targetRoomId, text.slice(0, 40).trim());
      }

      setIsStreaming(true);
      setStreamingText("");
      let accumulated = "";

      abortRef.current = subscribeTask(text, {
        sessionId: targetRoomId,
        model,
        onDelta(delta) {
          accumulated += delta;
          setStreamingText(accumulated);
        },
        onDone() {
          appendMessage("agent", accumulated);
          setStreamingText("");
          setIsStreaming(false);
          onMessageSaved?.();
        },
        onError(err) {
          setError(err.message);
          setStreamingText("");
          setIsStreaming(false);
        },
      });
    },
    [roomId, appendMessage, onRoomTitled, onMessageSaved]
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
    setStreamingText("");
  }, []);

  return { messages, streamingText, isStreaming, error, send, abort, loadHistory };
}
