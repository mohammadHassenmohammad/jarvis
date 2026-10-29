"""
Layered Context Management Service for J.A.R.V.I.S.
Maintains strict conversation isolation, long-context coherence across hundreds of messages,
and manages prompt budgeting.

Layers:
  - Layer A: Recent message window (most recent turns of the active conversation).
  - Layer B: Rolling conversation summary (incremental summary of older dialogue).
  - Layer C: Structured conversation facts (entities, goals, decisions, corrections).
  - Layer D: Original message retrieval (exact quotes, code, errors from older messages in this conversation).
  - Layer E: Permanent personal memory (the ONLY cross-chat context, strictly bounded by relevance).
"""

import json
import logging
import re
from typing import Any, Optional
from ..database.db import (
    get_messages,
    get_conversation_context,
    upsert_conversation_context,
    search_conversation_messages,
    get_relevant_memories,
    get_setting
)
from ..config import settings

logger = logging.getLogger("jarvis.context")


class ContextService:
    """
    Manages isolated conversational context across short and long chats (100+ messages).
    """

    RECENT_WINDOW_SIZE: int = 8  # Layer A: 8 most recent messages
    SUMMARY_TRIGGER_THRESHOLD: int = 10  # Messages count before rolling summary is generated
    SUMMARY_INTERVAL: int = 6  # Incremental update frequency

    @classmethod
    def extract_structured_facts(cls, messages: list[dict[str, Any]]) -> list[str]:
        """
        Extracts key goals, constraints, confirmed decisions, and user corrections from messages.
        """
        facts: list[str] = []
        seen = set()

        for msg in messages:
            content = msg.get("content", "").strip()
            role = msg.get("role", "")
            lower = content.lower()

            # 1. Corrections: "Actually ...", "Correction: ...", "No, it is ..."
            correction_match = re.search(r'\b(?:actually|correction|instead|change that to|not .+, but)\b[,\s]*(.+)', content, re.IGNORECASE)
            if correction_match:
                snippet = f"Correction: {correction_match.group(0).strip()}"
                if snippet not in seen:
                    facts.append(snippet)
                    seen.add(snippet)

            # 2. Explicit User Goals & Task Directives
            goal_match = re.search(r'\b(?:my goal is|we need to|the goal is|i want to build|our objective is)\b[,\s]*(.+)', content, re.IGNORECASE)
            if goal_match and role == "user":
                snippet = f"Goal: {goal_match.group(0).strip()}"
                if snippet not in seen:
                    facts.append(snippet)
                    seen.add(snippet)

            # 3. Decisions & Conclusions: "Decision: ...", "We agreed on ..."
            decision_match = re.search(r'\b(?:we agreed on|decision|let us go with|let\'s use|chosen)\b[,\s]*(.+)', content, re.IGNORECASE)
            if decision_match:
                snippet = f"Decision: {decision_match.group(0).strip()}"
                if snippet not in seen:
                    facts.append(snippet)
                    seen.add(snippet)

        return facts[-8:]

    @classmethod
    def generate_incremental_summary(
        cls,
        existing_summary: str,
        older_messages: list[dict[str, Any]]
    ) -> str:
        """
        Generates or updates a deterministic rolling summary of older parts of the conversation.
        Preserves core intent, facts, entities, decisions, and established corrections.
        """
        if not older_messages:
            return existing_summary

        summary_points: list[str] = []
        if existing_summary:
            summary_points.append(existing_summary.strip())

        # Group turns by speaker
        for i, m in enumerate(older_messages):
            role = "User" if m["role"] == "user" else "JARVIS"
            content = m["content"].strip()
            # Clean content of long code blocks or verbose text
            content_clean = re.sub(r'```[\s\S]*?```', '[code snippet]', content)
            if len(content_clean) > 200:
                content_clean = content_clean[:200] + "..."

            # Focus on key informational exchanges
            lower = content_clean.lower()
            if any(k in lower for k in ["goal", "build", "error", "fixed", "decided", "agreed", "project", "name", "fact", "port", "config", "actually"]):
                summary_points.append(f"{role}: {content_clean}")
            elif i % 2 == 0 and len(summary_points) < 12:
                # Keep periodic landmark turns
                summary_points.append(f"{role}: {content_clean}")

        # Keep rolling summary concise (capped at ~8 key points)
        if len(summary_points) > 10:
            summary_points = summary_points[-10:]

        return "\n".join(f"- {p.lstrip('- ')}" for p in summary_points)

    @classmethod
    def update_rolling_summary_if_needed(cls, conversation_id: str, all_messages: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Ensures a chat-scoped rolling summary and structured facts are maintained
        when a conversation extends beyond the recent message window.
        """
        context_record = get_conversation_context(conversation_id)
        current_summary = context_record.get("summary", "") if context_record else ""
        current_facts = context_record.get("structured_facts", []) if context_record else []
        last_msg_count = context_record.get("message_count_at_summary", 0) if context_record else 0

        total_msgs = len(all_messages)
        # Check if we should update rolling summary
        if total_msgs >= cls.SUMMARY_TRIGGER_THRESHOLD and (total_msgs - last_msg_count >= cls.SUMMARY_INTERVAL or not current_summary):
            # Messages to summarize: all older messages outside the recent window
            older_slice = all_messages[:-cls.RECENT_WINDOW_SIZE] if total_msgs > cls.RECENT_WINDOW_SIZE else all_messages
            new_summary = cls.generate_incremental_summary(current_summary, older_slice)
            extracted_facts = cls.extract_structured_facts(all_messages)
            last_id = older_slice[-1]["id"] if older_slice else (all_messages[-1]["id"] if all_messages else None)

            updated = upsert_conversation_context(
                conversation_id=conversation_id,
                summary=new_summary,
                structured_facts=extracted_facts,
                last_summarized_message_id=last_id,
                message_count_at_summary=total_msgs
            )
            return updated

        return context_record or {
            "conversation_id": conversation_id,
            "summary": current_summary,
            "structured_facts": current_facts
        }

    @classmethod
    def update_conversation_summary(
        cls,
        conversation_id: str,
        new_summary: str,
        key_facts: Optional[list[str]] = None,
        decisions: Optional[list[str]] = None,
        user_corrections: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Explicitly updates or stores a structured rolling summary and key facts for a conversation.
        """
        facts: list[str] = []
        if key_facts:
            facts.extend(key_facts)
        if decisions:
            facts.extend([f"Decision: {d}" if not d.startswith("Decision:") else d for d in decisions])
        if user_corrections:
            facts.extend([f"Correction: {c}" if not c.startswith("Correction:") else c for c in user_corrections])

        return upsert_conversation_context(
            conversation_id=conversation_id,
            summary=new_summary,
            structured_facts=facts
        )

    @classmethod
    def assemble_context(
        cls,
        conversation_id: str,
        user_message: str,
        system_base_prompt: str = settings.JARVIS_SYSTEM_PROMPT,
        include_tools: bool = False
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Assembles layered conversation context strictly following Section 4 precedence:
          1. System and safety instructions.
          2. Current user message.
          3. Relevant recent messages from the active conversation (Layer A).
          4. Relevant rolling summary and structured facts from that conversation (Layers B & C).
          5. Relevant permanent personal memories (Layer E - strictly bounded).
          6. Relevant older message excerpts from active chat if user query references past details (Layer D).
        """
        all_messages = get_messages(conversation_id)

        # 1. Update rolling summary for this conversation
        context_data = cls.update_rolling_summary_if_needed(conversation_id, all_messages)
        rolling_summary = context_data.get("summary", "")
        structured_facts = context_data.get("structured_facts", [])

        # 2. Layer A: Recent Message Window
        recent_messages = all_messages[-cls.RECENT_WINDOW_SIZE:] if len(all_messages) > cls.RECENT_WINDOW_SIZE else all_messages
        recent_ids = {m["id"] for m in recent_messages}

        # 3. Layer D: Original message retrieval for older details in this conversation
        # If user asks about earlier statements, errors, or numbers from this chat
        older_retrieved_snippets = []
        q_lower = user_message.lower()
        needs_historical_lookup = any(k in q_lower for k in [
            "earlier", "previously", "in the beginning", "first message", "original",
            "what was the error", "what did i say", "what did you say", "what was the number",
            "recall", "remember when we", "what did we decide", "code you gave"
        ])
        if needs_historical_lookup or len(all_messages) > cls.RECENT_WINDOW_SIZE:
            older_matches = search_conversation_messages(conversation_id, user_message, limit=3)
            # Only include older messages that are NOT already in the recent message window
            for om in older_matches:
                if om["id"] not in recent_ids:
                    role_label = "User" if om["role"] == "user" else "JARVIS"
                    older_retrieved_snippets.append(f"[{om['created_at'][:19]}] {role_label}: {om['content'][:300]}")

        # 4. Layer E: Permanent Personal Memories (the ONLY cross-chat context, strictly bounded by relevance)
        memory_enabled = get_setting("memory_enabled", "true").lower() == "true"
        relevant_memories = []
        if memory_enabled:
            relevant_memories = get_relevant_memories(user_message, limit=4)

        # 5. Assemble Context Blocks into System Prompt
        system_prompt = system_base_prompt.strip()

        # Add Layer B: Chat-specific Rolling Summary
        if rolling_summary:
            system_prompt += f"\n\n[Active Conversation Summary & History]:\n{rolling_summary}\n(This is the background context for the current conversation. Honor established decisions and corrections.)"

        # Add Layer C: Structured Conversation Facts & Decisions
        if structured_facts:
            facts_text = "\n".join(f"- {f}" for f in structured_facts)
            system_prompt += f"\n\n[Key Decisions & Constraints in this Conversation]:\n{facts_text}"

        # Add Layer D: Relevant Older Messages from THIS Conversation
        if older_retrieved_snippets:
            older_text = "\n".join(older_retrieved_snippets)
            system_prompt += f"\n\n[Referenced Older Messages from this Conversation]:\n{older_text}"

        # Add Layer E: Relevant Permanent Personal Memories (Cross-Chat)
        if relevant_memories:
            mem_text = "\n".join(f"- {m['content']}" for m in relevant_memories)
            system_prompt += f"\n\n[Permanent Personal Memories]:\n{mem_text}\n(These are permanent preferences and facts across sessions. Strictly apply them when relevant.)"

        if include_tools:
            system_prompt += "\n\nWhen asked to execute computer actions or check system stats, invoke the relevant tool immediately."

        # Format recent messages for the chat history stream
        formatted_messages = []
        for msg in recent_messages:
            m_dict: dict[str, Any] = {"role": msg["role"], "content": msg["content"]}
            if msg.get("tool_calls"):
                m_dict["tool_calls"] = msg["tool_calls"]
            formatted_messages.append(m_dict)

        return system_prompt, formatted_messages


context_service = ContextService()
