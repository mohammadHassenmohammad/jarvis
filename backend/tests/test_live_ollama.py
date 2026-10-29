import asyncio
import sys
import json
from backend.app.services.chat_service import chat_service
from backend.app.database.db import create_conversation, get_messages

async def main():
    print("[*] Creating test conversation...")
    c = create_conversation("Milestone 2 Real Verification")
    print(f"[*] Conversation ID: {c['id']}")
    print("[*] Streaming response from Qwen3:4b...")
    
    events = []
    async for raw_sse in chat_service.stream_chat(c['id'], "What is the current time?"):
        if raw_sse.startswith("data: "):
            payload = json.loads(raw_sse[6:].strip())
            events.append(payload)
            if payload.get("type") == "chunk":
                print(payload.get("content"), end="", flush=True)
            elif payload.get("type") == "executing_tool":
                print(f"\n[JARVIS Tool Executing]: {payload.get('tool')}({payload.get('arguments')})")
            elif payload.get("type") == "tool_result":
                print(f"\n[JARVIS Tool Result]: {payload.get('result')}\n")

    print("\n\n[*] Total events received:", len(events))
    msgs = get_messages(c['id'])
    print(f"[*] Messages persisted in DB: {len(msgs)}")

if __name__ == "__main__":
    asyncio.run(main())
