/**
 * TDD: a2aClient.js SSE 스트리밍 클라이언트 단위 테스트
 *
 * fetch API와 ReadableStream을 mock으로 대체하여 실제 서버 없이 테스트합니다.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { subscribeTask } from "../api/a2aClient.js";


// ── SSE 응답 스트림 생성 헬퍼 ──────────────────────────────────────────────────

function makeEventLines(events) {
  return events
    .map((e) => `data: ${JSON.stringify(e)}\n\n`)
    .join("");
}

function makeStream(text) {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(text);
  return new ReadableStream({
    start(controller) {
      controller.enqueue(bytes);
      controller.close();
    },
  });
}

function makeFetchResponse(events, { status = 200 } = {}) {
  const text = makeEventLines(events);
  return {
    ok: status >= 200 && status < 300,
    status,
    body: makeStream(text),
  };
}


// ── 표준 SSE 이벤트 픽스처 ────────────────────────────────────────────────────

const SUBMITTED_EVENT = {
  type: "task_status_update",
  task_id: "t-1",
  status: { state: "submitted" },
  final: false,
};

const ARTIFACT_EVENT = (text, lastChunk = false) => ({
  type: "task_artifact_update",
  task_id: "t-1",
  artifact: {
    index: 0,
    parts: [{ type: "text", text }],
    last_chunk: lastChunk,
  },
});

const COMPLETED_EVENT = {
  type: "task_status_update",
  task_id: "t-1",
  status: { state: "completed" },
  final: true,
};

const ERROR_EVENT = {
  type: "error",
  message: "서버 내부 오류",
};


// ── 테스트 ────────────────────────────────────────────────────────────────────

describe("subscribeTask", () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  // ── 기본 동작 ──────────────────────────────────────────────────────────────

  it("sends POST to /chat", async () => {
    fetchMock.mockResolvedValue(
      makeFetchResponse([SUBMITTED_EVENT, COMPLETED_EVENT])
    );

    await new Promise((resolve) => {
      subscribeTask("안녕", { onDelta: vi.fn(), onDone: resolve, onError: vi.fn() });
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/chat",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("sends Content-Type: application/json header", async () => {
    fetchMock.mockResolvedValue(
      makeFetchResponse([SUBMITTED_EVENT, COMPLETED_EVENT])
    );

    await new Promise((resolve) => {
      subscribeTask("test", { onDelta: vi.fn(), onDone: resolve, onError: vi.fn() });
    });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers["Content-Type"]).toBe("application/json");
  });

  it("sends correct JSON-RPC 2.0 payload structure", async () => {
    fetchMock.mockResolvedValue(
      makeFetchResponse([SUBMITTED_EVENT, COMPLETED_EVENT])
    );

    await new Promise((resolve) => {
      subscribeTask("테스트 메시지", { onDelta: vi.fn(), onDone: resolve, onError: vi.fn() });
    });

    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body);

    expect(body.jsonrpc).toBe("2.0");
    expect(body.method).toBe("message/stream");
    expect(body.params.message.role).toBe("user");
    expect(body.params.message.parts[0].text).toBe("테스트 메시지");
  });

  it("includes session_id when provided", async () => {
    fetchMock.mockResolvedValue(
      makeFetchResponse([SUBMITTED_EVENT, COMPLETED_EVENT])
    );

    await new Promise((resolve) => {
      subscribeTask("hi", {
        sessionId: "room-abc",
        onDelta: vi.fn(),
        onDone: resolve,
        onError: vi.fn(),
      });
    });

    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.params.session_id).toBe("room-abc");
  });

  it("includes model in metadata when provided", async () => {
    fetchMock.mockResolvedValue(
      makeFetchResponse([SUBMITTED_EVENT, COMPLETED_EVENT])
    );

    await new Promise((resolve) => {
      subscribeTask("hi", {
        model: "gpt-4o-mini",
        onDelta: vi.fn(),
        onDone: resolve,
        onError: vi.fn(),
      });
    });

    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.params.metadata.model).toBe("gpt-4o-mini");
  });

  it("omits metadata when model is not provided", async () => {
    fetchMock.mockResolvedValue(
      makeFetchResponse([SUBMITTED_EVENT, COMPLETED_EVENT])
    );

    await new Promise((resolve) => {
      subscribeTask("hi", { onDelta: vi.fn(), onDone: resolve, onError: vi.fn() });
    });

    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.params.metadata).toBeUndefined();
  });

  // ── 스트리밍 콜백 ──────────────────────────────────────────────────────────

  it("calls onDelta with each text chunk", async () => {
    const events = [
      SUBMITTED_EVENT,
      ARTIFACT_EVENT("안녕"),
      ARTIFACT_EVENT("하세요"),
      COMPLETED_EVENT,
    ];
    fetchMock.mockResolvedValue(makeFetchResponse(events));

    const deltas = [];
    await new Promise((resolve) => {
      subscribeTask("hi", {
        onDelta: (text) => deltas.push(text),
        onDone: resolve,
        onError: vi.fn(),
      });
    });

    expect(deltas).toEqual(["안녕", "하세요"]);
  });

  it("calls onDone when final status event received", async () => {
    const events = [SUBMITTED_EVENT, ARTIFACT_EVENT("ok"), COMPLETED_EVENT];
    fetchMock.mockResolvedValue(makeFetchResponse(events));

    const doneMock = vi.fn();
    await new Promise((resolve) => {
      subscribeTask("hi", {
        onDelta: vi.fn(),
        onDone: () => { doneMock(); resolve(); },
        onError: vi.fn(),
      });
    });

    expect(doneMock).toHaveBeenCalledOnce();
  });

  it("calls onDone as fallback when stream ends without final event", async () => {
    // final=false 이벤트만 있고 스트림이 종료됨
    const events = [SUBMITTED_EVENT, ARTIFACT_EVENT("토큰")];
    fetchMock.mockResolvedValue(makeFetchResponse(events));

    const doneMock = vi.fn();
    await new Promise((resolve) => {
      subscribeTask("hi", {
        onDelta: vi.fn(),
        onDone: () => { doneMock(); resolve(); },
        onError: vi.fn(),
      });
    });

    expect(doneMock).toHaveBeenCalledOnce();
  });

  // ── 에러 처리 ──────────────────────────────────────────────────────────────

  it("calls onError when error event received", async () => {
    const events = [SUBMITTED_EVENT, ERROR_EVENT];
    fetchMock.mockResolvedValue(makeFetchResponse(events));

    const errorMock = vi.fn();
    await new Promise((resolve) => {
      subscribeTask("hi", {
        onDelta: vi.fn(),
        onDone: vi.fn(),
        onError: (err) => { errorMock(err); resolve(); },
      });
    });

    expect(errorMock).toHaveBeenCalledOnce();
    expect(errorMock.mock.calls[0][0].message).toBe("서버 내부 오류");
  });

  it("calls onError when HTTP response is not ok", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, body: makeStream("") });

    const errorMock = vi.fn();
    await new Promise((resolve) => {
      subscribeTask("hi", {
        onDelta: vi.fn(),
        onDone: vi.fn(),
        onError: (err) => { errorMock(err); resolve(); },
      });
    });

    expect(errorMock).toHaveBeenCalledOnce();
    expect(errorMock.mock.calls[0][0].message).toContain("500");
  });

  it("does not call onError when request is aborted", async () => {
    fetchMock.mockRejectedValue(Object.assign(new Error("aborted"), { name: "AbortError" }));

    const errorMock = vi.fn();
    const controller = subscribeTask("hi", {
      onDelta: vi.fn(),
      onDone: vi.fn(),
      onError: errorMock,
    });

    controller.abort();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(errorMock).not.toHaveBeenCalled();
  });

  // ── AbortController ────────────────────────────────────────────────────────

  it("returns an AbortController", () => {
    fetchMock.mockResolvedValue(makeFetchResponse([SUBMITTED_EVENT, COMPLETED_EVENT]));
    const controller = subscribeTask("hi", {
      onDelta: vi.fn(),
      onDone: vi.fn(),
      onError: vi.fn(),
    });
    expect(controller).toBeInstanceOf(AbortController);
  });

  it("passes AbortController signal to fetch", async () => {
    fetchMock.mockResolvedValue(makeFetchResponse([SUBMITTED_EVENT, COMPLETED_EVENT]));

    await new Promise((resolve) => {
      subscribeTask("hi", { onDelta: vi.fn(), onDone: resolve, onError: vi.fn() });
    });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.signal).toBeInstanceOf(AbortSignal);
  });

  // ── SSE 파싱 ──────────────────────────────────────────────────────────────

  it("ignores lines that do not start with 'data: '", async () => {
    const rawText = "event: ping\ndata: " + JSON.stringify(COMPLETED_EVENT) + "\n\n";
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      body: makeStream(rawText),
    });

    const doneMock = vi.fn();
    await new Promise((resolve) => {
      subscribeTask("hi", {
        onDelta: vi.fn(),
        onDone: () => { doneMock(); resolve(); },
        onError: vi.fn(),
      });
    });

    expect(doneMock).toHaveBeenCalledOnce();
  });

  it("silently skips malformed JSON in SSE lines", async () => {
    const rawText = "data: {invalid json}\n\ndata: " + JSON.stringify(COMPLETED_EVENT) + "\n\n";
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      body: makeStream(rawText),
    });

    const doneMock = vi.fn();
    await new Promise((resolve) => {
      subscribeTask("hi", {
        onDelta: vi.fn(),
        onDone: () => { doneMock(); resolve(); },
        onError: vi.fn(),
      });
    });

    expect(doneMock).toHaveBeenCalledOnce();
  });

  it("does not call onDelta for empty text parts", async () => {
    const events = [
      ARTIFACT_EVENT(""),
      ARTIFACT_EVENT("실제 텍스트"),
      COMPLETED_EVENT,
    ];
    fetchMock.mockResolvedValue(makeFetchResponse(events));

    const deltas = [];
    await new Promise((resolve) => {
      subscribeTask("hi", {
        onDelta: (t) => deltas.push(t),
        onDone: resolve,
        onError: vi.fn(),
      });
    });

    expect(deltas).toEqual(["실제 텍스트"]);
  });
});
