"""
TDD: room_store DB 연산 테스트 (aiomysql mock 처리)

실제 DB 없이 커넥션 풀과 커서 동작을 mock으로 대체합니다.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── async 컨텍스트 매니저 헬퍼 ──────────────────────────────────────────────────

class AsyncContextManagerMock:
    """async with 구문을 지원하는 mock"""
    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass


def _make_pool_mock(cursor_mock):
    """aiomysql 커넥션 풀 mock 생성"""
    conn_mock = MagicMock()
    conn_mock.cursor = MagicMock(return_value=AsyncContextManagerMock(cursor_mock))
    conn_mock.commit = AsyncMock()
    pool_mock = MagicMock()
    pool_mock.acquire = MagicMock(return_value=AsyncContextManagerMock(conn_mock))
    return pool_mock


# ── create_room ────────────────────────────────────────────────────────────────

class TestCreateRoom:
    @pytest.mark.asyncio
    async def test_returns_room_dict(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            room = await room_store.create_room()

        assert "id" in room
        assert "title" in room
        assert "created_at" in room
        assert "updated_at" in room

    @pytest.mark.asyncio
    async def test_default_title_is_new_chat(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            room = await room_store.create_room()

        assert room["title"] == "New Chat"

    @pytest.mark.asyncio
    async def test_custom_title(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            room = await room_store.create_room(title="나의 채팅방")

        assert room["title"] == "나의 채팅방"

    @pytest.mark.asyncio
    async def test_custom_room_id_used(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            room = await room_store.create_room(room_id="custom-id-123")

        assert room["id"] == "custom-id-123"

    @pytest.mark.asyncio
    async def test_inserts_into_rooms_table(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            await room_store.create_room()

        # INSERT 쿼리 호출 확인
        call_args = cursor.execute.call_args_list[0]
        assert "INSERT INTO rooms" in call_args[0][0]


# ── list_rooms ─────────────────────────────────────────────────────────────────

class TestListRooms:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[
            {"id": "r1", "title": "방1", "created_at": 1000, "updated_at": 2000},
            {"id": "r2", "title": "방2", "created_at": 1000, "updated_at": 3000},
        ])
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            rooms = await room_store.list_rooms()

        assert len(rooms) == 2
        assert rooms[0]["id"] == "r1"

    @pytest.mark.asyncio
    async def test_query_orders_by_updated_at_desc(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            await room_store.list_rooms()

        call_args = cursor.execute.call_args[0][0]
        assert "ORDER BY updated_at DESC" in call_args


# ── save_message ───────────────────────────────────────────────────────────────

class TestSaveMessage:
    @pytest.mark.asyncio
    async def test_returns_message_dict(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            msg = await room_store.save_message("room-1", "user", "안녕하세요")

        assert msg["room_id"] == "room-1"
        assert msg["role"] == "user"
        assert msg["content"] == "안녕하세요"

    @pytest.mark.asyncio
    async def test_executes_two_queries(self):
        """메시지 INSERT + rooms updated_at UPDATE — 2개 쿼리"""
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            await room_store.save_message("room-1", "agent", "응답")

        assert cursor.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_first_query_inserts_message(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            await room_store.save_message("room-1", "user", "테스트")

        first_call = cursor.execute.call_args_list[0][0][0]
        assert "INSERT INTO messages" in first_call

    @pytest.mark.asyncio
    async def test_second_query_updates_room_timestamp(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            await room_store.save_message("room-1", "user", "테스트")

        second_call = cursor.execute.call_args_list[1][0][0]
        assert "UPDATE rooms SET updated_at" in second_call


# ── get_messages ───────────────────────────────────────────────────────────────

class TestGetMessages:
    @pytest.mark.asyncio
    async def test_returns_messages_for_room(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[
            {"id": "m1", "room_id": "r1", "role": "user", "content": "안녕", "created_at": 1000},
            {"id": "m2", "room_id": "r1", "role": "agent", "content": "반가워요", "created_at": 2000},
        ])
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            messages = await room_store.get_messages("r1")

        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "agent"

    @pytest.mark.asyncio
    async def test_query_orders_by_created_at_asc(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.fetchall = AsyncMock(return_value=[])
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            await room_store.get_messages("r1")

        call_args = cursor.execute.call_args[0][0]
        assert "ORDER BY created_at ASC" in call_args


# ── delete_room ────────────────────────────────────────────────────────────────

class TestDeleteRoom:
    @pytest.mark.asyncio
    async def test_returns_true_when_deleted(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.rowcount = 1
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            result = await room_store.delete_room("room-1")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.rowcount = 0
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            result = await room_store.delete_room("nonexistent-room")

        assert result is False

    @pytest.mark.asyncio
    async def test_executes_delete_query(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        cursor.rowcount = 1
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            await room_store.delete_room("room-1")

        call_args = cursor.execute.call_args[0][0]
        assert "DELETE FROM rooms" in call_args


# ── update_room_title ──────────────────────────────────────────────────────────

class TestUpdateRoomTitle:
    @pytest.mark.asyncio
    async def test_executes_update_query(self):
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        pool = _make_pool_mock(cursor)

        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            await room_store.update_room_title("room-1", "새 제목")

        call_args = cursor.execute.call_args[0][0]
        assert "UPDATE rooms SET title" in call_args

    @pytest.mark.asyncio
    async def test_title_truncation_behavior(self):
        """task_handler는 40자로 잘라서 전달 — 여기서는 그대로 저장"""
        cursor = MagicMock()
        cursor.execute = AsyncMock()
        pool = _make_pool_mock(cursor)

        long_title = "a" * 50
        with patch("room_store.get_pool", AsyncMock(return_value=pool)):
            import room_store
            await room_store.update_room_title("room-1", long_title)

        # room_store 자체는 자르지 않음 — caller 책임
        params = cursor.execute.call_args[0][1]
        assert params[0] == long_title
