import { useState, useEffect, useCallback, useRef } from "react";
import { getAgents, addAgent, removeAgent } from "../api/agentRegistryClient.js";

const POLL_INTERVAL = 10_000; // 10초마다 상태 갱신

export function useAgentRegistry() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getAgents();
      setAgents(data);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }, []);

  // 초기 로드 + 폴링
  useEffect(() => {
    refresh();
    timerRef.current = setInterval(refresh, POLL_INTERVAL);
    return () => clearInterval(timerRef.current);
  }, [refresh]);

  const add = useCallback(async (url) => {
    setLoading(true);
    try {
      const agent = await addAgent(url);
      setAgents((prev) => [...prev, agent]);
      setError(null);
      return null;
    } catch (e) {
      return e.message;
    } finally {
      setLoading(false);
    }
  }, []);

  const remove = useCallback(async (url) => {
    setLoading(true);
    try {
      await removeAgent(url);
      setAgents((prev) => prev.filter((a) => a.url !== url));
      setError(null);
      return null;
    } catch (e) {
      return e.message;
    } finally {
      setLoading(false);
    }
  }, []);

  return { agents, loading, error, refresh, add, remove };
}
