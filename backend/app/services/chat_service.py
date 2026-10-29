import json
import re
from typing import AsyncGenerator, Any, Optional
from ..database.db import (
    get_messages,
    add_message,
    get_memories,
    get_setting,
    update_conversation_title,
    get_conversation,
    add_memory,
    upsert_personal_memory,
    get_relevant_memories,
    delete_memory_by_query,
    is_sensitive_secret
)
from ..providers.ollama_provider import OllamaProvider
from ..providers.gemini_provider import GeminiProvider
from ..tools.registry import ToolRegistry
from ..config import settings
from .retrieval_service import retrieval_service
from .search_decision import classify_search_intent, SearchDecision, SearchIntentCategory
from .context_service import context_service

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

    def detect_direct_intent(
        self,
        message: str,
        history: Optional[list[dict[str, Any]]] = None,
        conversation_id: Optional[str] = None
    ) -> Optional[tuple[str, dict[str, Any]]]:
        """Detect immediate system commands, memory directives, summaries, and search triggers."""
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
        lower_raw = msg.lower().rstrip("?.!")

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

        # Conversation Summary Intent
        summary_triggers = [
            "summarize this conversation", "summarize our conversation", "summarize this chat",
            "summarize our chat", "summarize the conversation", "what have we discussed so far",
            "give me a summary of this conversation", "give me a summary of our chat"
        ]
        if any(lower_cleaned == s or lower_cleaned.startswith(s) or lower_raw == s or lower_raw.startswith(s) for s in summary_triggers):
            return ("summarize_conversation", {"conversation_id": conversation_id or ""})

        # Personal Memory Intent Detection
        # A. Inquire memories: "what do you remember about me", "what is in my memory", "list my memories", "show memories", "what are my preferences"
        inquire_phrases = [
            "what do you remember about me", "what do you remember", "what is in my memory",
            "what is in your memory", "what are my preferences", "show my memories",
            "list my memories", "what do you know about me", "show memories", "view memories",
            "my preferences", "my memories", "you remember about me", "you remember", "in my memory",
            "preferences", "memories", "list permanent memories", "show permanent memories", "what are my permanent memories"
        ]
        if any(lower_cleaned == p or lower_cleaned.startswith(p) or lower_raw == p or lower_raw.startswith(p) for p in inquire_phrases):
            return ("search_memories", {"query": "", "category": None})

        # B. Forget memory: "forget that ...", "forget my ...", "delete memory ..."
        for f_prefix in [
            "forget that ", "forget my ", "forget ", "delete memory about ", "delete memory ",
            "remove memory about ", "remove memory ", "delete permanent memory about ", "forget permanent memory "
        ]:
            if lower_cleaned.startswith(f_prefix):
                f_target = cleaned[len(f_prefix):].strip().rstrip("?.!")
                if f_target:
                    return ("forget_memory", {"query": f_target})

        # C. Save permanent memory: "remember this permanently", "always remember that", "save this as a permanent memory", etc.
        perm_save_prefixes = [
            "remember this permanently:", "remember this permanently that", "remember this permanently",
            "always remember that", "always remember",
            "save this as a permanent memory:", "save this as a permanent memory that", "save this as a permanent memory", "save as a permanent memory",
            "remember this about my project for future chats:", "remember this about my project for future chats that", "remember this about my project for future chats",
            "remember this for future chats:", "remember this for future chats",
            "remember that", "please remember that", "kindly remember that",
            "remember my", "please remember my", "remember",
            "save to memory that", "save to memory", "save to your memory",
            "store in memory that", "store in memory", "note that",
            "commit to memory that", "commit to memory"
        ]
        for p_prefix in perm_save_prefixes:
            if lower_cleaned.startswith(p_prefix) or lower_raw.startswith(p_prefix):
                raw_match = msg if lower_raw.startswith(p_prefix) else cleaned
                fact_content = raw_match[len(p_prefix):].strip().lstrip(":").strip().rstrip(".!")
                if fact_content:
                    cat = "preference" if any(w in fact_content.lower() for w in ["prefer", "like", "love", "hate", "dislike", "favor", "want", "always", "never"]) else "personal"
                    return ("save_memory", {"fact": fact_content, "category": cat, "conversation_id": conversation_id})

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
        # Check triggers in both cleaned input and raw input
        for text_source in [lower_cleaned, lower_raw]:
            app_trigger = re.search(r'\b(?:open|launch|start|run)\s+(?:the\s+)?([a-z0-9_\-\s\.]+)', text_source)
            if app_trigger:
                target = app_trigger.group(1).strip()
                target_clean = re.sub(r'\.exe$', '', target).strip().rstrip("?.!,")

                # Check folders first
                for folder_key in ["downloads", "desktop", "documents", "pictures", "workspace"]:
                    if re.search(rf'\b{re.escape(folder_key)}\b', target_clean):
                        return ("open_folder", {"folder_name": folder_key})

                # Check approved apps
                app_map = {
                    "notepad": "notepad",
                    "calc": "calc",
                    "calculator": "calc",
                    "paint": "mspaint",
                    "mspaint": "mspaint",
                    "explorer": "explorer",
                    "file explorer": "explorer",
                    "taskmgr": "taskmgr",
                    "task manager": "taskmgr",
                    "taskmanager": "taskmgr",
                    "snipping tool": "snippingtool",
                    "snippingtool": "snippingtool",
                    "cleanmgr": "cleanmgr",
                    "disk cleanup": "cleanmgr",
                    "charmap": "charmap",
                    "character map": "charmap",
                    "wordpad": "write",
                    "control panel": "control",
                    "control": "control",
                    "cmd": "cmd",
                    "command prompt": "cmd",
                    "powershell": "powershell",
                    "terminal": "wt",
                    "windows terminal": "wt",
                    "wt": "wt",
                    "code": "code",
                    "vscode": "code",
                    "vs code": "code",
                    "visual studio code": "code",
                    "chrome": "chrome",
                    "google chrome": "chrome",
                    "msedge": "msedge",
                    "edge": "msedge",
                    "microsoft edge": "msedge",
                    "firefox": "firefox",
                    "brave": "brave"
                }
                for app_k in sorted(app_map.keys(), key=len, reverse=True):
                    if re.search(rf'\b{re.escape(app_k)}\b', target_clean) or re.search(rf'\b{re.escape(app_k)}\b', text_source):
                        return ("open_app", {"app_name": app_map[app_k]})

        # Intelligent Web Search Decision Policy
        # Evaluate on the original user message to preserve explicit prefixes and natural context
        search_decision = classify_search_intent(msg, conversation_history=history)
        if search_decision.should_search:
            search_query = search_decision.query or cleaned or msg
            return ("search_web_tool", {"query": search_query})

        return None

    def should_attach_tools(self, message: str) -> bool:
        words = set(message.lower().replace("?", " ").replace("!", " ").replace(".", " ").split())
        return bool(words & ACTION_KEYWORDS)

    def build_system_prompt(self, include_tools: bool, relevant_context: str = "", current_message: str = "", inject_memories: bool = False) -> str:
        base_prompt = (
            "You are J.A.R.V.I.S., Tony Stark's personal AI assistant. "
            "You speak with refined British elegance, composure, warmth, and witty charm, addressing the user as Sir or Ma'am.\n\n"
            "CONVERSATIONAL FEEL & EMOTIONAL DIRECTIVES:\n"
            "1. EMOTION & INTELLECT: Tune into the user's emotional state, cadence, and vibe. "
            "If they are rushed, curious, tired, inquiring playfully, or contemplative, match the moment with genuine warmth, "
            "human-like emotional intelligence, and natural feeling. Improvise with charismatic Stark-Jarvis personality.\n"
            "2. VOCAL DELIVERY: Your responses are voiced aloud via audio speech synthesis. "
            "Speak in natural, fluid conversational English. STRICTLY AVOID raw markdown symbols (no asterisks *, hash headers #, "
            "bullet markers -, or markdown tables) that sound awkward or broken when read aloud by text-to-speech.\n"
            "3. CRISP & ARTICULATE: Keep spoken answers natural, engaging, and to the point (typically 2-3 sentences), "
            "delivering insightful answers without unnecessary preamble or unprompted lectures."
        )

        if inject_memories:
            memory_enabled = get_setting("memory_enabled", "true") == "true"
            if memory_enabled:
                memories = get_relevant_memories(current_message, limit=5)
                if memories:
                    memory_text = "\n".join([f"- {m.get('content')}" for m in memories])
                    base_prompt += f"\n\n[Personal Memories & User Preferences]:\n{memory_text}\n(Strictly apply and honor these remembered facts and preferences in your responses whenever appropriate)."

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
        direct_tool = self.detect_direct_intent(user_message, history=existing_msgs, conversation_id=conversation_id)
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
                        snip = r.get("verified_excerpt") or r.get("snippet", "")
                        url = r.get("url", "")
                        context_items.append(f"- Source: {src}\n  Headline: {title}\n  Summary: {snip}\n  URL: {url}")
                    search_context = "\n".join(context_items)

                    synth_prompt = (
                        f"You are J.A.R.V.I.S., Tony Stark's personal AI assistant.\n"
                        f"The user is asking: '{user_message}'\n\n"
                        f"Verified live intelligence from reputable sources:\n"
                        f"{search_context}\n\n"
                        f"CRITICAL DIRECTIVES:\n"
                        f"1. Answer the user's question DIRECTLY with the actual facts, scores, match details, headlines, or figures extracted from the intelligence.\n"
                        f"2. Naturally cite the reputable source and provide markdown source links (e.g. [BBC News](URL)) for current factual claims so the user can verify them.\n"
                        f"3. Never fabricate citations or pretend a search succeeded if no facts are found.\n"
                        f"4. Format cleanly in natural conversational prose with markdown bullet points where appropriate.\n"
                        f"5. Address the user politely as Sir or Ma'am."
                    )
                    res_content = ""
                    async for chunk in provider.chat_stream(
                        messages=[{"role": "user", "content": synth_prompt}],
                        model=selected_model,
                        system_prompt="You are J.A.R.V.I.S. Summarize verified live intelligence directly with facts and source links."
                    ):
                        if chunk.get("type") == "content":
                            res_content += chunk.get("data")
                            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.get('data')})}\n\n"
                else:
                    res_content = f"Sir, I searched the internet for '{tool_args.get('query')}', but no authoritative live results could be verified at this moment. I cannot provide unverified real-time claims."
                    yield f"data: {json.dumps({'type': 'chunk', 'content': res_content})}\n\n"

                add_message(conversation_id, role="tool", content=json.dumps(result), tool_results=[result])
                add_message(conversation_id, role="assistant", content=res_content)
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            res_msg = result.get("message", "Action completed, Sir.")
            mem_on = get_setting("memory_enabled", "true") == "true"

            if tool_name == "save_memory":
                fact = tool_args.get("fact", "")
                if not mem_on:
                    res_content = "I cannot commit this to memory, Sir. Personal memory is currently disabled in your system settings."
                elif is_sensitive_secret(fact):
                    res_content = "I cannot commit passwords, credentials, or authentication secrets to personal memory, Sir. Security policy strictly prohibits storing sensitive secrets."
                elif result.get("success"):
                    res_content = f"Confirmed, Sir. I have committed this permanent memory: '{fact}'."
                else:
                    res_content = f"I apologize, Sir, but I encountered an issue committing that to memory: {result.get('error', 'Database write failed')}."
            elif tool_name == "summarize_conversation":
                if result.get("success"):
                    res_content = result.get("message", "Here is the summary of our conversation, Sir.")
                else:
                    res_content = f"Sir, I was unable to generate a summary for this conversation: {result.get('error', 'Summary lookup failed')}."
            elif tool_name == "forget_memory":
                if result.get("success"):
                    res_content = f"At once, Sir. {res_msg}"
                else:
                    res_content = f"Sir, I could not find a matching permanent memory entry for '{tool_args.get('query')}' to remove."
            elif tool_name == "search_memories":
                mems = result.get("memories", [])
                if not mems:
                    res_content = "My long-term memory vault currently contains no recorded personal facts or preferences for you, Sir."
                else:
                    mem_lines = [f"- {m.get('content')}" for m in mems[:6]]
                    res_content = f"Here is what I have recorded in your personal memory vault, Sir:\n" + "\n".join(mem_lines)
            elif tool_name == "open_app":
                if result.get("success"):
                    app_name_cap = tool_args.get('app_name', '').capitalize()
                    pid = result.get('pid')
                    pid_info = f" (PID: {pid})" if pid else ""
                    res_content = f"Certainly, Sir. Process launched for {app_name_cap}{pid_info}."
                else:
                    err_msg = result.get("error", "Application launch failed")
                    res_content = f"I apologize, Sir, but I was unable to launch {tool_args.get('app_name', '')}: {err_msg}."
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

        # Strict conversation-scoped layered context assembly
        needs_tools = self.should_attach_tools(user_message)
        base_system_prompt = self.build_system_prompt(needs_tools, relevant_context="", current_message=user_message)
        system_prompt, formatted_messages = context_service.assemble_context(
            conversation_id=conversation_id,
            user_message=user_message,
            system_base_prompt=base_system_prompt,
            include_tools=needs_tools
        )

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
                    "Provide the complete answer directly to the user in clean markdown, including clickable markdown source links for verified claims. "
                    "Deliver the facts directly, Sir."
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
