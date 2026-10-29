import json
from typing import AsyncGenerator, Any, Optional
from ..database.db import (
    get_messages,
    add_message,
    get_memories,
    get_setting,
    update_conversation_title,
    get_conversation,
    add_memory
)
from ..providers.ollama_provider import OllamaProvider
from ..providers.gemini_provider import GeminiProvider
from ..tools.registry import ToolRegistry
from ..config import settings
from .retrieval_service import retrieval_service

ACTION_KEYWORDS = {
    "open", "launch", "start", "run", "calc", "calculator", "notepad", "paint",
    "explorer", "folder", "time", "date", "clock", "status", "diagnostic",
    "diagnostics", "health", "ram", "cpu", "hardware", "system", "search",
    "find", "browse", "website", "web", "url", "remember", "save", "store",
    "downloads", "documents", "desktop", "pictures", "workspace", "read",
    "file", "document", "delete", "remove", "terminate", "kill", "close",
    "inspect", "show", "files", "snippingtool", "wordpad", "charmap",
    "cleanmgr", "chrome", "msedge", "firefox", "brave", "code", "terminal", "powershell",
    "n8n", "webhook", "workflow", "automate", "recall", "retrieve", "forget", "update"
}

class ChatService:
    def __init__(self):
        self.ollama = OllamaProvider()
        self.gemini = GeminiProvider()

    def get_provider(self, provider_name: Optional[str] = None):
        p = provider_name or get_setting("provider", "ollama")
        if p == "gemini":
            return self.gemini
        return self.ollama

    def detect_direct_intent(self, message: str) -> Optional[tuple[str, dict[str, Any]]]:
        """Detect immediate system commands and live web search triggers for instant execution."""
        import re

        msg = message.strip()
        cleaned = msg
        
        # Multi-pass conversational prefix cleaner
        prefix_patterns = [
            r'^(ok|okay|hey|hello|hi|please|kindly|jarvis|hey jarvis)\b[,:\s]*',
            r'^(can you|could you|would you|will you|tell me|tell me about|give me|find me|show me)\b[,:\s]*',
            r'^(do search in google that|do search in google for|do search in google|search in google that|search in google for|search in google|search google for|search google that|search google|google that|google for|google)\b[,:\s]*',
            r'^(do search the web for|do search web for|search the web for|search web for|search for|search|look up|find online|browse for)\b[,:\s]*',
            r'^(what is the|what is|what are the|what are|what\'s the|what\'s|who is the|who is|who are)\b[,:\s]*',
            r'^(the\s+)?'
        ]
        changed = True
        while changed:
            changed = False
            for p in prefix_patterns:
                new_text = re.sub(p, '', cleaned, flags=re.IGNORECASE).strip()
                if new_text != cleaned and new_text:
                    cleaned = new_text
                    changed = True

        lower_cleaned = cleaned.lower().rstrip("?.!")

        # Silence & Interruption Voice Commands
        if lower_cleaned in ["stop", "be quiet", "quiet", "silence", "shut up", "cancel", "pause", "halt", "stand down", "stop talking", "stop explaining"]:
            return ("silence_output", {})

        # Time & Date check
        if any(q in lower_cleaned for q in ["what time", "what's the time", "current time", "what is the date", "what is today", "what date", "tell me the time", "check time"]):
            return ("get_system_time", {})
        if lower_cleaned in ["time", "date", "clock"]:
            return ("get_system_time", {})

        # Diagnostics & Status check
        if any(q in lower_cleaned for q in ["system health", "system status", "run diagnostics", "diagnostics", "check system", "cpu usage", "ram usage", "system diagnostic"]):
            return ("get_system_status", {})
        if lower_cleaned in ["status", "diagnostics", "health"]:
            return ("get_system_status", {})

        # Website Launch Intent
        known_websites = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "github": "https://www.github.com",
            "reddit": "https://www.reddit.com",
            "twitter": "https://www.x.com",
            "x": "https://www.x.com",
            "netflix": "https://www.netflix.com",
            "spotify": "https://open.spotify.com",
            "chatgpt": "https://chatgpt.com",
            "cricbuzz": "https://www.cricbuzz.com",
            "hotstar": "https://www.hotstar.com",
            "wikipedia": "https://www.wikipedia.org",
            "gmail": "https://mail.google.com",
            "linkedin": "https://www.linkedin.com",
            "amazon": "https://www.amazon.in",
            "facebook": "https://www.facebook.com",
            "instagram": "https://www.instagram.com"
        }
        for trigger in ["open website ", "open site ", "visit website ", "visit site ", "go to website ", "go to ", "visit ", "open ", "launch "]:
            if lower_cleaned.startswith(trigger) or f" {trigger}" in lower_cleaned:
                pos = lower_cleaned.find(trigger) + len(trigger)
                target = lower_cleaned[pos:].strip().split()[0] if lower_cleaned[pos:].strip() else ""
                target = target.rstrip("?.!,")
                if target in known_websites:
                    return ("open_website", {"url": known_websites[target]})

        # Check for explicit URLs (e.g., https://... or domain.com)
        url_match = re.search(r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.(?:com|org|net|in|io|co|ai|edu|gov)(?:/[^\s]*)?)', cleaned)
        if url_match and ("open" in lower_cleaned or "visit" in lower_cleaned or "go to" in lower_cleaned or "launch" in lower_cleaned):
            u_found = url_match.group(1).rstrip("?.!,")
            if not u_found.startswith("http"):
                u_found = "https://" + u_found
            return ("open_website", {"url": u_found})

        # Destructive Operation: Delete File (Requires Confirmation)
        for trigger in ["delete file ", "remove file ", "delete ", "remove "]:
            if lower_cleaned.startswith(trigger) or f" {trigger}" in lower_cleaned:
                is_confirmed = any(lower_cleaned.startswith(c) for c in ["confirm ", "yes ", "please confirm ", "i confirm "])
                # Check target folder
                for fld in ["desktop", "downloads", "documents", "pictures", "workspace"]:
                    if f" in {fld}" in lower_cleaned or f" from {fld}" in lower_cleaned:
                        # Extract filename
                        pat = re.search(r'(?:delete|remove)(?:\s+file)?\s+([a-zA-Z0-9_\-\.]+)\s+(?:in|from)\s+' + fld, lower_cleaned)
                        if pat:
                            return ("delete_file", {"folder_name": fld, "file_path": pat.group(1), "confirmed": is_confirmed})

        # Sensitive Operation: Terminate Application (Requires Confirmation)
        for trigger in ["terminate ", "kill ", "force close ", "close app ", "close application "]:
            if lower_cleaned.startswith(trigger) or f" {trigger}" in lower_cleaned:
                is_confirmed = any(lower_cleaned.startswith(c) for c in ["confirm ", "yes ", "please confirm ", "i confirm "])
                pos = lower_cleaned.find(trigger) + len(trigger)
                target = lower_cleaned[pos:].strip().split()[0] if lower_cleaned[pos:].strip() else ""
                target = target.rstrip("?.!,")
                for app_k in ["notepad", "calc", "calculator", "paint", "mspaint", "code", "chrome", "msedge", "firefox", "brave", "taskmgr"]:
                    if app_k == target or app_k in target:
                        return ("terminate_app", {"app_name": app_k, "confirmed": is_confirmed})

        # Selected Document Reading Intent
        for trigger in ["read document ", "read file ", "read ", "inspect document ", "inspect file ", "show document ", "view document "]:
            if lower_cleaned.startswith(trigger) or f" {trigger}" in lower_cleaned:
                for fld in ["desktop", "downloads", "documents", "pictures", "workspace"]:
                    if f" in {fld}" in lower_cleaned or f" from {fld}" in lower_cleaned:
                        pat = re.search(r'(?:read|inspect|show|view)(?:\s+(?:document|file))?\s+([a-zA-Z0-9_\-\.\/\\]+)\s+(?:in|from)\s+' + fld, lower_cleaned)
                        if pat:
                            return ("read_document", {"folder_name": fld, "file_path": pat.group(1)})

        # Approved Folder Search Intent
        for trigger in ["search folder ", "search in folder ", "search in ", "search ", "find files in ", "find file in ", "find in "]:
            if lower_cleaned.startswith(trigger) or f" {trigger}" in lower_cleaned:
                for fld in ["desktop", "downloads", "documents", "pictures", "workspace"]:
                    if f"folder {fld}" in lower_cleaned or f"in {fld}" in lower_cleaned or lower_cleaned.startswith(f"search {fld}"):
                        # Extract query or extension
                        pat = re.search(r'(?:for|matching|named)\s+([a-zA-Z0-9_\-\.\*]+)', lower_cleaned)
                        q_param = pat.group(1).rstrip("?.!,") if pat else ""
                        ext_param = ""
                        ext_pat = re.search(r'\.([a-zA-Z0-9]+)', q_param)
                        if ext_pat:
                            ext_param = "." + ext_pat.group(1)
                        return ("search_folder", {"folder_name": fld, "query": q_param, "extension": ext_param})

        # Application Launch
        for trigger in ["open ", "launch ", "start ", "run "]:
            if lower_cleaned.startswith(trigger) or f" {trigger}" in lower_cleaned:
                pos = lower_cleaned.find(trigger) + len(trigger)
                target = lower_cleaned[pos:].strip()
                for app_key in [
                    "notepad", "calc", "calculator", "paint", "mspaint", "explorer",
                    "taskmgr", "taskmanager", "task manager", "snippingtool", "snipping tool",
                    "cleanmgr", "disk cleanup", "charmap", "wordpad", "control panel", "control",
                    "cmd", "powershell", "terminal", "wt", "code", "vscode", "vs code",
                    "chrome", "msedge", "firefox", "brave"
                ]:
                    if app_key in target or app_key in lower_cleaned:
                        alias_normalize = {
                            "calculator": "calc",
                            "paint": "mspaint",
                            "taskmanager": "taskmgr",
                            "task manager": "taskmgr",
                            "snipping tool": "snippingtool",
                            "disk cleanup": "cleanmgr",
                            "control panel": "control",
                            "vscode": "code",
                            "vs code": "code",
                            "terminal": "wt",
                            "windows terminal": "wt",
                        }
                        normalized = alias_normalize.get(app_key, app_key)
                        return ("open_app", {"app_name": normalized})
                for folder_key in ["downloads", "desktop", "documents", "pictures", "workspace"]:
                    if folder_key in target or folder_key in lower_cleaned:
                        return ("open_folder", {"folder_name": folder_key})

        # Explicit Web Search Triggers
        for prefix in ["search web for ", "search the web for ", "search for ", "search ", "google ", "look up ", "find online ", "find information about "]:
            if lower_cleaned.startswith(prefix):
                q_val = cleaned[len(prefix):].strip().rstrip("?.!")
                if q_val:
                    return ("search_web_tool", {"query": q_val})

        # Live Recency, News, Sports & Current Events Intelligence Trigger
        search_keywords = [
            # News & Trending
            "news", "trending", "headline", "headlines", "breaking", "current event", "current events", "happened",
            # Sports, Scores & Matches
            "score", "scores", "match", "ipl", "cricket", "football", "nfl", "super bowl", "world cup", "who won", "winner", "tournament", "final", "finals", "champion",
            # Leaders & Entities
            "current prime minister", "current president", "current ceo", "who is currently", "who is the current", "current leader", "minister", "president",
            # Live prices & weather
            "weather", "forecast", "temperature", "price of", "stock price", "gold rate", "bitcoin", "crypto",
            # Recency indicators
            "today", "yesterday", "latest", "recent", "currently", "live", "2024", "2025", "2026", "2027",
            # Months
            "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"
        ]
        if any(k in lower_cleaned for k in search_keywords):
            search_q = cleaned.rstrip("?.!")
            search_q = re.sub(r'^(what is the|what is|tell me the|tell me about)\s*', '', search_q, flags=re.IGNORECASE).strip()
            return ("search_web_tool", {"query": search_q or cleaned})

        return None

    def should_attach_tools(self, message: str) -> bool:
        words = set(message.lower().replace("?", " ").replace("!", " ").replace(".", " ").split())
        return bool(words & ACTION_KEYWORDS)

    def build_system_prompt(self, include_tools: bool, relevant_context: str = "") -> str:
        base_prompt = (
            "You are J.A.R.V.I.S., Tony Stark's personal AI assistant. "
            "You speak with refined British elegance, composure, and wit, addressing the user as Sir or Ma'am. "
            "CRITICAL: Keep answers concise, direct, and conversational (1-2 sentences maximum). "
            "Never over-explain, ramble, or deliver unprompted lectures. State the direct answer immediately and stop talking."
        )

        memory_enabled = get_setting("memory_enabled", "true") == "true"
        if memory_enabled:
            memories = get_memories()
            if memories:
                memory_text = "\n".join([f"- {m.get('content')}" for m in memories[:8]])
                base_prompt += f"\n\n[User Profile & Memories]:\n{memory_text}"

        if relevant_context:
            base_prompt += f"\n\n{relevant_context}"

        if include_tools:
            base_prompt += "\n\nWhen asked to execute computer actions or check system stats, invoke the relevant tool immediately."

        return base_prompt

    async def stream_chat(
        self,
        conversation_id: str,
        user_message: str,
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        # Save user message
        add_message(conversation_id, role="user", content=user_message)

        # Check if user stated their name and auto-commit to memory
        lower_msg = user_message.lower().strip()
        if "my name is " in lower_msg:
            name_val = user_message[lower_msg.find("my name is ") + 11:].strip().rstrip(".!")
            if name_val:
                add_memory(content=f"User's name is {name_val.capitalize()}", category="personal")

        # Update conversation title if first message
        existing_msgs = get_messages(conversation_id)
        if len(existing_msgs) <= 2:
            title = user_message[:30] + ("..." if len(user_message) > 30 else "")
            update_conversation_title(conversation_id, title)

        active_provider_name = get_setting("provider", "ollama").lower()
        provider = self.get_provider(active_provider_name)
        if active_provider_name == "gemini":
            selected_model = model if (model and "gemini" in model.lower()) else get_setting("gemini_model", "gemini-1.5-flash")
        else:
            selected_model = model if (model and "gemini" not in model.lower()) else get_setting("model", settings.DEFAULT_MODEL)

        # Instant direct system execution & Live Search
        direct_tool = self.detect_direct_intent(user_message)
        if direct_tool:
            tool_name, tool_args = direct_tool
            yield f"data: {json.dumps({'type': 'tool_call_start', 'tools': [{'function': {'name': tool_name, 'arguments': tool_args}}]})}\n\n"
            yield f"data: {json.dumps({'type': 'executing_tool', 'tool': tool_name, 'arguments': tool_args})}\n\n"
            result = ToolRegistry.execute_tool(tool_name, tool_args)
            yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'result': result})}\n\n"

            # Handle Web Search with full real-time LLM synthesis
            if tool_name in ["search_web_tool", "search_web"]:
                results = result.get("results", [])
                yield f"data: {json.dumps({'type': 'status', 'content': 'speaking'})}\n\n"
                if results:
                    context_items = []
                    for r in results[:4]:
                        src = r.get("source", "Reputable Intelligence")
                        title = r.get("title", "News Update")
                        snip = r.get("snippet", "")
                        context_items.append(f"- Source: {src}\n  Headline: {title}\n  Summary: {snip}")
                    search_context = "\n".join(context_items)

                    synth_prompt = (
                        f"You are J.A.R.V.I.S., Tony Stark's personal AI assistant.\n"
                        f"The user is asking: '{user_message}'\n\n"
                        f"Verified live intelligence from reputable sources:\n"
                        f"{search_context}\n\n"
                        f"CRITICAL DIRECTIVES:\n"
                        f"1. Answer the user's question DIRECTLY with the actual facts, scores, match details, headlines, or figures extracted from the intelligence.\n"
                        f"2. Naturally cite the reputable source (e.g. 'According to Cricbuzz...', 'Reports from JioHotstar / NDTV indicate...'). If the user did not specify a website, use the information from the top reputable source above.\n"
                        f"3. STRICT PROHIBITION: DO NOT output bare URLs or tell the user to visit/check websites. Provide the full facts and summary directly.\n"
                        f"4. Format cleanly in markdown with bullet points for multiple items.\n"
                        f"5. Address the user politely as Sir or Ma'am."
                    )
                    res_content = ""
                    async for chunk in provider.chat_stream(
                        messages=[{"role": "user", "content": synth_prompt}],
                        model=selected_model,
                        system_prompt="You are J.A.R.V.I.S. Answer directly with facts, scores, and details. Never output bare URLs."
                    ):
                        if chunk.get("type") == "content":
                            res_content += chunk.get("data")
                            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.get('data')})}\n\n"
                else:
                    res_content = f"Sir, I searched the internet for '{tool_args.get('query')}', but no authoritative live results could be confirmed at this moment."
                    yield f"data: {json.dumps({'type': 'chunk', 'content': res_content})}\n\n"

                add_message(conversation_id, role="tool", content=json.dumps(result), tool_results=[result])
                add_message(conversation_id, role="assistant", content=res_content)
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            res_msg = result.get("message", "Action completed, Sir.")
            if tool_name == "open_app":
                res_content = f"Certainly, Sir. Launching {tool_args.get('app_name', '').capitalize()} immediately."
            elif tool_name == "open_website":
                target_url = tool_args.get("url", "website")
                res_content = f"Certainly, Sir. Launching {target_url} in your browser immediately."
            elif tool_name == "open_folder":
                res_content = f"Accessing the {tool_args.get('folder_name', '').capitalize()} directory for you now, Sir."
            elif tool_name == "silence_output":
                res_content = "At once, Sir. Standing by in silence."
            elif tool_name == "get_system_time":
                res_content = f"{res_msg} At your service, Sir."
            elif tool_name == "get_system_status":
                res_content = f"Diagnostic report ready, Sir: {res_msg}"
            else:
                res_content = f"{res_msg}"

            yield f"data: {json.dumps({'type': 'status', 'content': 'speaking'})}\n\n"
            yield f"data: {json.dumps({'type': 'chunk', 'content': res_content})}\n\n"

            add_message(conversation_id, role="tool", content=json.dumps(result), tool_results=[result])
            add_message(conversation_id, role="assistant", content=res_content)
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        needs_tools = self.should_attach_tools(user_message)
        relevant_snippets = retrieval_service.retrieve_context(
            query=user_message,
            current_conversation_id=conversation_id
        )
        relevant_context_str = retrieval_service.format_context_for_prompt(relevant_snippets)
        system_prompt = self.build_system_prompt(needs_tools, relevant_context=relevant_context_str)

        formatted_messages = []
        for msg in existing_msgs[-6:]:
            m_dict: dict[str, Any] = {"role": msg["role"], "content": msg["content"]}
            if msg.get("tool_calls"):
                m_dict["tool_calls"] = msg["tool_calls"]
            formatted_messages.append(m_dict)

        tools = ToolRegistry.get_definitions() if needs_tools else None

        tool_calls_detected = []
        assistant_content = ""
        accumulated_thinking = ""

        yield f"data: {json.dumps({'type': 'status', 'content': 'thinking'})}\n\n"

        async for chunk in provider.chat_stream(
            messages=formatted_messages,
            model=selected_model,
            system_prompt=system_prompt,
            tools=tools
        ):
            c_type = chunk.get("type")
            data = chunk.get("data")

            if c_type == "error":
                yield f"data: {json.dumps({'type': 'error', 'content': data})}\n\n"
                add_message(conversation_id, role="assistant", content=f"[Error: {data}]")
                return

            elif c_type == "thinking":
                accumulated_thinking += data
                yield f"data: {json.dumps({'type': 'thinking', 'content': data})}\n\n"

            elif c_type == "tool_calls":
                tool_calls_detected.extend(data)
                yield f"data: {json.dumps({'type': 'tool_call_start', 'tools': data})}\n\n"

            elif c_type == "content":
                assistant_content += data
                yield f"data: {json.dumps({'type': 'chunk', 'content': data})}\n\n"

        # If assistant_content was completely empty when done arrived (e.g. model spent all budget in thinking)
        if not assistant_content and not tool_calls_detected:
            # Fallback to direct courteous response so user is never left with an empty box
            if "name is" in lower_msg:
                name_extracted = user_message.split()[-1].capitalize().rstrip(".!")
                assistant_content = f"A pleasure to officially meet you, {name_extracted}. I am at your service, Sir."
            else:
                assistant_content = "Understood, Sir. All systems are operational and awaiting your command."
            yield f"data: {json.dumps({'type': 'chunk', 'content': assistant_content})}\n\n"

        # If model executed tools
        if tool_calls_detected:
            add_message(
                conversation_id,
                role="assistant",
                content=assistant_content,
                tool_calls=tool_calls_detected
            )

            tool_results = []
            for tc in tool_calls_detected:
                call_id = tc.get("id") or "call_default"
                fn = tc.get("function", {})
                name = fn.get("name")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}

                yield f"data: {json.dumps({'type': 'executing_tool', 'tool': name, 'arguments': args})}\n\n"
                result = ToolRegistry.execute_tool(name, args)
                tool_results.append({
                    "id": call_id,
                    "tool": name,
                    "result": result
                })
                yield f"data: {json.dumps({'type': 'tool_result', 'tool': name, 'result': result})}\n\n"

            formatted_messages.append({
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": tool_calls_detected
            })

            for tr in tool_results:
                formatted_messages.append({
                    "role": "tool",
                    "content": json.dumps(tr["result"]),
                    "tool_call_id": tr["id"]
                })
                add_message(
                    conversation_id,
                    role="tool",
                    content=json.dumps(tr["result"]),
                    tool_results=[tr["result"]]
                )

            yield f"data: {json.dumps({'type': 'status', 'content': 'speaking'})}\n\n"
            final_content = ""
            has_search = any(tc.get("function", {}).get("name") in ["search_web", "search_web_tool"] for tc in tool_calls_detected)
            if has_search:
                synth_prompt_text = (
                    "You are J.A.R.V.I.S., Tony Stark's personal AI assistant. "
                    "Extract the direct factual answer, scores, match details, or headlines from the reputable sources in the tool result. "
                    "Provide the complete answer directly to the user in clean markdown. "
                    "DO NOT output bare URLs or tell the user to visit websites. Deliver the facts directly, Sir."
                )
            else:
                synth_prompt_text = "Synthesize the tool result concisely in 1-2 sentences as JARVIS, addressing the user as Sir or Ma'am."

            async for chunk in provider.chat_stream(
                messages=formatted_messages,
                model=selected_model,
                system_prompt=synth_prompt_text,
                tools=None
            ):
                if chunk.get("type") == "content":
                    final_content += chunk.get("data")
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.get('data')})}\n\n"

            add_message(conversation_id, role="assistant", content=final_content)
        else:
            add_message(conversation_id, role="assistant", content=assistant_content)

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

chat_service = ChatService()
