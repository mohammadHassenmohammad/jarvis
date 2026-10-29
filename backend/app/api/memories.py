from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..database.db import (
    get_memories,
    get_memory,
    add_memory,
    update_memory,
    delete_memory,
    search_memories
)

router = APIRouter(prefix="/api/memories", tags=["Memories"])

class MemoryCreate(BaseModel):
    content: str
    category: Optional[str] = "user_preference"

class MemoryUpdate(BaseModel):
    content: str
    category: Optional[str] = None

@router.get("")
def list_memories(
    q: Optional[str] = Query(None, description="Optional search term"),
    category: Optional[str] = Query(None, description="Optional category filter")
):
    if q or (category and category != "all"):
        return {"memories": search_memories(query=q or "", category=category)}
    return {"memories": get_memories()}

@router.get("/search")
def search_memory_vault(
    q: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None)
):
    results = search_memories(query=q, category=category)
    return {"memories": results, "count": len(results)}

@router.get("/{memory_id}")
def read_single_memory(memory_id: str):
    mem = get_memory(memory_id)
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"memory": mem}

@router.post("")
def create_memory(mem: MemoryCreate):
    if not mem.content or not mem.content.strip():
        raise HTTPException(status_code=400, detail="Memory content cannot be empty")
    new_mem = add_memory(content=mem.content.strip(), category=mem.category or "user_preference")
    return {"memory": new_mem}

@router.put("/{memory_id}")
def edit_memory(memory_id: str, mem: MemoryUpdate):
    if not mem.content or not mem.content.strip():
        raise HTTPException(status_code=400, detail="Memory content cannot be empty")
    success = update_memory(memory_id, content=mem.content.strip(), category=mem.category)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    updated_record = get_memory(memory_id)
    return {"success": True, "memory": updated_record}

@router.delete("/{memory_id}")
def remove_memory(memory_id: str):
    success = delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True}
