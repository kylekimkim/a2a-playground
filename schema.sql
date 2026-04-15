-- ============================================================
-- GPT A2A Chat — MariaDB DDL
-- ============================================================

CREATE DATABASE IF NOT EXISTS a2a_chat
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE a2a_chat;

-- ============================================================
-- 채팅방 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS rooms (
    id         CHAR(36)     NOT NULL                        COMMENT '채팅방 UUID (PK)',
    title      VARCHAR(100) NOT NULL DEFAULT 'New Chat'     COMMENT '채팅방 제목 (첫 메시지 앞 40자)',
    model      VARCHAR(50)  NOT NULL DEFAULT 'gpt-5.4-mini' COMMENT '사용 모델 ID',
    created_at BIGINT       NOT NULL                        COMMENT '생성 시각 (Unix ms)',
    updated_at BIGINT       NOT NULL                        COMMENT '마지막 메시지 시각 (Unix ms)',

    PRIMARY KEY (id),
    INDEX idx_rooms_updated (updated_at DESC)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='채팅방';


-- ============================================================
-- 채팅 메시지 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    id         CHAR(36)                        NOT NULL COMMENT '메시지 UUID (PK)',
    room_id    CHAR(36)                        NOT NULL COMMENT '채팅방 ID (FK)',
    role       ENUM('user', 'agent')           NOT NULL COMMENT '발화자 (user | agent)',
    content    TEXT                            NOT NULL COMMENT '메시지 내용',
    created_at BIGINT                          NOT NULL COMMENT '전송 시각 (Unix ms)',

    PRIMARY KEY (id),
    INDEX idx_messages_room_time (room_id, created_at ASC),

    CONSTRAINT fk_messages_room
        FOREIGN KEY (room_id)
        REFERENCES rooms (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='채팅 메시지';
