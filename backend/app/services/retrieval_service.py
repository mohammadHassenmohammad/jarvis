import logging
from typing import Any, Optional
from ..database.db import (
    search_relevant_conversations,
    get_messages,
    get_setting
)

logger = logging.getLogger("jarvis.retrieval")

class ConversationRetrievalService:
    """
    Local-first, privacy-preserving conversation retrieval engine.
    
    Searches past session dialogues for relevant context when the user asks questions,
    allowing cross-session recall without sending data to third parties.
    """

    @classmethod
    def is_enabled(cls) -> bool:
        return get_setting("retrieval_enabled", "true").lower() == "true"

    @classmethod
    def get_max_snippets(cls) -> int:
        try:
            val = get_setting("retrieval_limit", "3")
            return max(1, min(int(val or "3"), 8))
        except Exception:
            return 3

    @classmethod
    def retrieve_context(
        cls,
        query: str,
        current_conversation_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant message pairs from past conversations.
        """
        if not cls.is_enabled():
            return []

        clean_q = (query or "").strip()
        # Skip trivial single-word or short greetings
        if len(clean_q) < 4 or clean_q.lower() in ("hi", "hello", "hey", "test", "ok", "yes", "no"):
            return []

        max_items = limit or cls.get_max_snippets()
        matches = search_relevant_conversations(
            query=clean_q,
            exclude_conversation_id=current_conversation_id,
            limit=max_items
        )

        if not matches:
            return []

        # Group matches into coherent conversational exchanges
        enhanced_snippets: list[dict[str, Any]] = []
        seen_convs: set[str] = set()

        for match in matches:
            cid = match.get("conversation_id")
            if not cid or cid in seen_convs:
                continue
            seen_convs.add(cid)

            # Retrieve conversation messages to find neighbor messages for context
            conv_msgs = get_messages(cid)
            match_idx = -1
            for idx, m in enumerate(conv_msgs):
                if m.get("id") == match.get("id"):
                    match_idx = idx
                    break

            snippet_text = ""
            if match_idx != -1:
                # Include preceding message or following response if available
                start_i = max(0, match_idx - 1)
                end_i = min(len(conv_msgs), match_idx + 2)
                dialogue_lines = []
                for m in conv_msgs[start_i:end_i]:
                    speaker = "User" if m["role"] == "user" else "JARVIS"
                    content = m["content"].strip()
                    # Truncate very long messages for prompt compactness
                    if len(content) > 250:
                        content = content[:250] + "..."
                    dialogue_lines.append(f"{speaker}: {content}")
                snippet_text = "\n    ".join(dialogue_lines)
            else:
                speaker = "User" if match["role"] == "user" else "JARVIS"
                snippet_text = f"{speaker}: {match['content'][:250]}"

            enhanced_snippets.append({
                "conversation_id": cid,
                "title": match.get("conversation_title") or "Archived Session",
                "date": match.get("created_at", "")[:10],
                "score": match.get("relevance_score", 0),
                "snippet": snippet_text
            })

            if len(enhanced_snippets) >= max_items:
                break

        return enhanced_snippets

    @classmethod
    def format_context_for_prompt(cls, snippets: list[dict[str, Any]]) -> str:
        """
        Format retrieved snippets into a concise context block for LLM system prompt.
        """
        if not snippets:
            return ""

        lines = ["[Relevant Prior Conversation Context]:"]
        for s in snippets:
            title = s.get("title", "Session")
            date = s.get("date", "")
            lines.append(f"- Session '{title}' ({date}):\n    {s['snippet']}")

        return "\n".join(lines)

retrieval_service = ConversationRetrievalService()
