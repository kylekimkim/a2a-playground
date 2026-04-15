/**
 * TDD: roomsClient.js REST 클라이언트 단위 테스트
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  listRooms,
  createRoom,
  deleteRoom,
  getRoomMessages,
  updateRoomTitle,
} from "../api/roomsClient.js";


function makeFetchJson(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  };
}

function makeFetchNoContent() {
  return { ok: true, status: 204, json: async () => null };
}


describe("roomsClient", () => {
  let fetchMock;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  // ── listRooms ──────────────────────────────────────────────────────────────

  describe("listRooms", () => {
    it("sends GET /rooms", async () => {
      fetchMock.mockResolvedValue(makeFetchJson([]));
      await listRooms();
      expect(fetchMock).toHaveBeenCalledWith("/rooms", expect.objectContaining({}));
    });

    it("returns array of rooms", async () => {
      const rooms = [{ id: "r1", title: "방1" }, { id: "r2", title: "방2" }];
      fetchMock.mockResolvedValue(makeFetchJson(rooms));
      const result = await listRooms();
      expect(result).toEqual(rooms);
    });

    it("returns empty array when no rooms", async () => {
      fetchMock.mockResolvedValue(makeFetchJson([]));
      const result = await listRooms();
      expect(result).toEqual([]);
    });
  });

  // ── createRoom ─────────────────────────────────────────────────────────────

  describe("createRoom", () => {
    it("sends POST /rooms", async () => {
      fetchMock.mockResolvedValue(makeFetchJson({ id: "new-room", title: "New Chat" }));
      await createRoom();
      const [, options] = fetchMock.mock.calls[0];
      expect(options.method).toBe("POST");
    });

    it("returns created room object", async () => {
      const room = { id: "r-new", title: "New Chat", created_at: 1000 };
      fetchMock.mockResolvedValue(makeFetchJson(room));
      const result = await createRoom();
      expect(result.id).toBe("r-new");
    });
  });

  // ── deleteRoom ─────────────────────────────────────────────────────────────

  describe("deleteRoom", () => {
    it("sends DELETE /rooms/{id}", async () => {
      fetchMock.mockResolvedValue(makeFetchNoContent());
      await deleteRoom("room-abc");
      const [url, options] = fetchMock.mock.calls[0];
      expect(url).toBe("/rooms/room-abc");
      expect(options.method).toBe("DELETE");
    });

    it("returns null for 204 No Content", async () => {
      fetchMock.mockResolvedValue(makeFetchNoContent());
      const result = await deleteRoom("room-abc");
      expect(result).toBeNull();
    });

    it("throws on non-ok response", async () => {
      fetchMock.mockResolvedValue(makeFetchJson({}, 404));
      await expect(deleteRoom("nonexistent")).rejects.toThrow("HTTP 404");
    });
  });

  // ── getRoomMessages ────────────────────────────────────────────────────────

  describe("getRoomMessages", () => {
    it("sends GET /rooms/{id}/messages", async () => {
      fetchMock.mockResolvedValue(makeFetchJson([]));
      await getRoomMessages("room-xyz");
      const [url] = fetchMock.mock.calls[0];
      expect(url).toBe("/rooms/room-xyz/messages");
    });

    it("returns messages array", async () => {
      const messages = [
        { id: "m1", role: "user", content: "안녕" },
        { id: "m2", role: "agent", content: "반가워요" },
      ];
      fetchMock.mockResolvedValue(makeFetchJson(messages));
      const result = await getRoomMessages("room-1");
      expect(result).toHaveLength(2);
      expect(result[0].role).toBe("user");
    });
  });

  // ── updateRoomTitle ────────────────────────────────────────────────────────

  describe("updateRoomTitle", () => {
    it("sends PATCH /rooms/{id}", async () => {
      fetchMock.mockResolvedValue(makeFetchJson({ id: "r1", title: "새 제목" }));
      await updateRoomTitle("r1", "새 제목");
      const [url, options] = fetchMock.mock.calls[0];
      expect(url).toBe("/rooms/r1");
      expect(options.method).toBe("PATCH");
    });

    it("sends title in body", async () => {
      fetchMock.mockResolvedValue(makeFetchJson({ id: "r1", title: "새 제목" }));
      await updateRoomTitle("r1", "새 제목");
      const [, options] = fetchMock.mock.calls[0];
      const body = JSON.parse(options.body);
      expect(body.title).toBe("새 제목");
    });

    it("throws on server error", async () => {
      fetchMock.mockResolvedValue(makeFetchJson({}, 500));
      await expect(updateRoomTitle("r1", "x")).rejects.toThrow("HTTP 500");
    });
  });

  // ── 공통 헤더 ──────────────────────────────────────────────────────────────

  describe("공통 요청 헤더", () => {
    it("sends Content-Type: application/json", async () => {
      fetchMock.mockResolvedValue(makeFetchJson([]));
      await listRooms();
      const [, options] = fetchMock.mock.calls[0];
      expect(options.headers["Content-Type"]).toBe("application/json");
    });
  });
});
