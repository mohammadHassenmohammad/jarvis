from typing import Any, Callable, Optional
from .system_tools import (
    get_system_time,
    get_system_status,
    open_app,
    open_folder,
    open_website,
    search_web_tool,
    save_memory_tool,
    search_folder,
    read_document,
    delete_file,
    terminate_app,
    update_memory_tool,
    delete_memory_tool,
    search_memories_tool,
    search_past_conversations_tool,
    trigger_n8n_webhook,
)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_system_time",
            "description": "Get current local time, date, day of week, and timezone on the user's computer.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Check host system performance, including CPU usage, RAM utilization, operating system, and health.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an approved desktop application from the strict security allowlist on the Windows computer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The name of the application to launch (e.g., 'notepad', 'calc', 'calculator', 'mspaint', 'taskmgr', 'snippingtool', 'explorer', 'code', 'chrome', 'msedge')."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_folder",
            "description": "Open an approved Windows directory in File Explorer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {
                        "type": "string",
                        "description": "The name of the folder to open (e.g. 'desktop', 'downloads', 'documents', 'pictures', 'workspace')."
                    }
                },
                "required": ["folder_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_folder",
            "description": "Securely search for files within approved Windows directories (desktop, downloads, documents, pictures, workspace).",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {
                        "type": "string",
                        "description": "Approved directory to search ('desktop', 'downloads', 'documents', 'pictures', 'workspace')."
                    },
                    "query": {
                        "type": "string",
                        "description": "Substring or filename to filter matches."
                    },
                    "extension": {
                        "type": "string",
                        "description": "Optional file extension filter (e.g. '.txt', '.pdf', '.py', '.json', '.docx')."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of search results to return (default 15)."
                    }
                },
                "required": ["folder_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_document",
            "description": "Safely read and inspect the text content of a document located in an approved directory (desktop, downloads, documents, pictures, workspace).",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {
                        "type": "string",
                        "description": "Approved directory containing the file ('desktop', 'downloads', 'documents', 'pictures', 'workspace')."
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Relative filename or path within the folder (e.g., 'notes.txt', 'project/readme.md')."
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Maximum characters to return for brevity (default 3000)."
                    }
                },
                "required": ["folder_name", "file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Permanently delete a specified file in an approved folder. SENSITIVE: Requires explicit user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {
                        "type": "string",
                        "description": "Approved directory containing the file ('desktop', 'downloads', 'documents', 'pictures', 'workspace')."
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Relative filename or path to delete."
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "Must be true only if the user has explicitly confirmed deletion."
                    }
                },
                "required": ["folder_name", "file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "terminate_app",
            "description": "Force close an allowlisted Windows application. SENSITIVE: Requires explicit user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the approved application to terminate (e.g. 'notepad', 'calc')."
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "Must be true only if the user has explicitly confirmed termination."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Open a website in the default Windows web browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full website URL to open (e.g. 'https://github.com', 'https://google.com')."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Perform an online search for recent information, facts, or news without requiring paid API keys.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Commit an important fact, user preference, or personal detail to long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "The fact or preference to remember."
                    },
                    "category": {
                        "type": "string",
                        "description": "Category for the memory (e.g., 'user_preference', 'work', 'personal')."
                    }
                },
                "required": ["fact"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_memory",
            "description": "Update or edit an existing piece of saved knowledge or preference in the memory vault.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The unique ID of the memory record to update."
                    },
                    "content": {
                        "type": "string",
                        "description": "The updated content for the memory."
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional updated category."
                    }
                },
                "required": ["memory_id", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_memory",
            "description": "Delete or forget a specific record from persistent long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "The unique ID of the memory record to remove."
                    }
                },
                "required": ["memory_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_memories",
            "description": "Search the persistent memory vault for saved user preferences, habits, or past recorded facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword or topic to search for."
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_past_conversations",
            "description": "Retrieve relevant dialogues, topics, and code discussed across past archived sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Topic, question, or keywords from earlier conversations to search."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of conversational excerpts to retrieve (default 4)."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_n8n_webhook",
            "description": "Trigger an optional self-hosted n8n automation webhook for workflow actions. Fails safely if disabled.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow_name": {
                        "type": "string",
                        "description": "Name or identifier of the n8n automation workflow to trigger."
                    },
                    "payload": {
                        "type": "object",
                        "description": "JSON dictionary of parameters to send to the n8n webhook."
                    }
                },
                "required": ["workflow_name"]
            }
        }
    }
]

TOOL_HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {
    "get_system_time": lambda **kw: get_system_time(),
    "get_system_status": lambda **kw: get_system_status(),
    "open_app": lambda app_name="", **kw: open_app(app_name=app_name),
    "open_folder": lambda folder_name="", **kw: open_folder(folder_name=folder_name),
    "search_folder": lambda folder_name="", query="", extension="", max_results=15, **kw: search_folder(folder_name=folder_name, query=query, extension=extension, max_results=max_results),
    "read_document": lambda folder_name="", file_path="", max_chars=3000, **kw: read_document(folder_name=folder_name, file_path=file_path, max_chars=max_chars),
    "delete_file": lambda folder_name="", file_path="", confirmed=False, **kw: delete_file(folder_name=folder_name, file_path=file_path, confirmed=confirmed),
    "terminate_app": lambda app_name="", confirmed=False, **kw: terminate_app(app_name=app_name, confirmed=confirmed),
    "open_website": lambda url="", **kw: open_website(url=url),
    "search_web": lambda query="", **kw: search_web_tool(query=query),
    "search_web_tool": lambda query="", **kw: search_web_tool(query=query),
    "save_memory": lambda fact="", category="user_preference", **kw: save_memory_tool(fact=fact, category=category),
    "update_memory": lambda memory_id="", content="", category=None, **kw: update_memory_tool(memory_id=memory_id, content=content, category=category),
    "delete_memory": lambda memory_id="", **kw: delete_memory_tool(memory_id=memory_id),
    "search_memories": lambda query="", category=None, **kw: search_memories_tool(query=query, category=category),
    "search_past_conversations": lambda query="", limit=4, **kw: search_past_conversations_tool(query=query, limit=limit),
    "trigger_n8n_webhook": lambda workflow_name="default", payload=None, **kw: trigger_n8n_webhook(workflow_name=workflow_name, payload=payload),
    "silence_output": lambda **kw: {"success": True, "message": "Voice silenced and standing by."},
}

class ToolRegistry:
    @staticmethod
    def get_definitions() -> list[dict[str, Any]]:
        return TOOL_DEFINITIONS

    @staticmethod
    def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Safely execute a tool after strict name & argument validation.
        Rejects arbitrary or non-allowlisted commands.
        """
        handler = TOOL_HANDLERS.get(name)
        if not handler:
            return {
                "success": False,
                "error": f"Tool '{name}' is not recognized or allowed by the security policy."
            }

        try:
            return handler(**arguments)
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error in tool '{name}': {str(e)}"
            }
