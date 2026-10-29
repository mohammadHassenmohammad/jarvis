from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any
from ..tools.registry import ToolRegistry
from ..config import settings

router = APIRouter(prefix="/api/tools", tags=["Tools"])

class ToolExecuteRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = {}

@router.get("")
def list_available_tools():
    return {
        "tools": ToolRegistry.get_definitions(),
        "allowed_apps": sorted(list(settings.ALLOWED_APPS.keys())),
        "allowed_folders": sorted(list(settings.ALLOWED_FOLDERS.keys())),
        "sensitive_tools": sorted(list(settings.SENSITIVE_TOOLS)),
        "allowed_document_extensions": sorted(list(settings.ALLOWED_DOCUMENT_EXTENSIONS))
    }

@router.post("/execute")
def execute_direct_tool(req: ToolExecuteRequest):
    result = ToolRegistry.execute_tool(req.name, req.arguments)
    return {"tool": req.name, "result": result}
