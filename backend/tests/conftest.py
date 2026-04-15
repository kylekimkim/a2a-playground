"""
공유 pytest 픽스처 및 경로 설정
"""
import sys
import os
import pytest

# backend 디렉토리를 sys.path에 추가 (로컬 임포트 지원)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── 공통 픽스처 ────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_room_id():
    return "test-room-1234-abcd"


@pytest.fixture
def sample_message_payload():
    return {
        "jsonrpc": "2.0",
        "id": "req-001",
        "method": "message/stream",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "안녕하세요"}],
            }
        },
    }


@pytest.fixture
def sample_message_payload_with_session(sample_room_id):
    return {
        "jsonrpc": "2.0",
        "id": "req-002",
        "method": "message/stream",
        "params": {
            "session_id": sample_room_id,
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "오늘 날씨 어때?"}],
            },
            "metadata": {"model": "gpt-4o-mini"},
        },
    }
