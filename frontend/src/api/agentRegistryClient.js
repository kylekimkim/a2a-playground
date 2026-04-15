const BASE = "http://localhost:8000/registry/agents";

export async function getAgents() {
  const res = await fetch(BASE);
  if (!res.ok) throw new Error("에이전트 목록 조회 실패");
  return res.json();
}

export async function addAgent(url) {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (res.status === 409) throw new Error("이미 등록된 에이전트입니다.");
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "에이전트 추가 실패");
  }
  return res.json();
}

export async function removeAgent(url) {
  const res = await fetch(BASE, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (res.status === 404) throw new Error("등록되지 않은 에이전트입니다.");
  if (!res.ok) throw new Error("에이전트 삭제 실패");
}
