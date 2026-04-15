from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import room_store

router = APIRouter()


class CreateRoomBody(BaseModel):
    title: str = "New Chat"


class UpdateRoomBody(BaseModel):
    title: str


@router.get("")
async def list_rooms():
    return await room_store.list_rooms()


@router.post("")
async def create_room(body: CreateRoomBody = CreateRoomBody()):
    return await room_store.create_room(title=body.title)


@router.patch("/{room_id}")
async def update_room(room_id: str, body: UpdateRoomBody):
    if not await room_store.room_exists(room_id):
        raise HTTPException(status_code=404, detail="Room not found")
    await room_store.update_room_title(room_id, body.title)
    return await room_store.get_room(room_id)


@router.delete("/{room_id}")
async def delete_room(room_id: str):
    deleted = await room_store.delete_room(room_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Room not found")
    return JSONResponse(status_code=204, content=None)


@router.get("/{room_id}/messages")
async def get_messages(room_id: str):
    if not await room_store.room_exists(room_id):
        raise HTTPException(status_code=404, detail="Room not found")
    return await room_store.get_messages(room_id)
