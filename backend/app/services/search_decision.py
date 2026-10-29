"""
Search Intent Decision Policy for J.A.R.V.I.S.
Classifies user queries into:
  - NO_SEARCH: Ordinary conversation, jokes, emotional support, stable educational concepts,
               follow-ups on existing context, or explicit 'do not search' requests.
  - SEARCH_REQUIRED: Current news, software versions, live sports, weather, prices, current facts.
  - EXPLICIT_SEARCH: User explicitly commanded a web search or online lookup.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class SearchIntentCategory(str, Enum):
    NO_SEARCH = "no_search"
    SEARCH_REQUIRED = "search_required"
    EXPLICIT_SEARCH = "explicit_search"


@dataclass
class SearchDecision:
    should_search: bool
    category: SearchIntentCategory
    reason: str
    query: str = ""


# Negative overrides: user explicitly requests NOT to search the web
NEGATIVE_SEARCH_PATTERNS = [
    r"\b(?:do not|don'?t)\s+search\b",
    r"\bwithout\s+searching\b",
    r"\banswer\s+from\s+(?:your\s+)?(?:existing\s+)?knowledge\b",
    r"\bfrom\s+(?:your\s+)?(?:own\s+)?knowledge\b",
    r"\bno\s+(?:web\s+)?search\b",
    r"\bskip\s+(?:the\s+)?search\b",
]

# Explicit search triggers: user directly asks to search the web or lookup online
EXPLICIT_SEARCH_PATTERNS = [
    (r"^(?:search\s+(?:the\s+)?web\s+for|search\s+web\s+for|search\s+for|google\s+for|google)\s+(.+)$", 1),
    (r"^(?:look\s+up|find\s+recent\s+sources\s+(?:on|for)|find\s+sources\s+for|find\s+online|find\s+information\s+about)\s+(.+)$", 1),
    (r"^(?:verify\s+this\s+online|verify\s+online(?::|\s+)?)\s*(.*)$", 1),
    (r"^(?:check\s+the\s+latest\s+information\s+about|browse\s+the\s+web\s+for)\s+(.+)$", 1),
]

# Ordinary conversation & jokes & emotional support (Category A)
ORDINARY_CONVERSATION_PATTERNS = [
    # Greetings
    r"^(?:hello|hi|hey|hey\s+jarvis|good\s+(?:morning|afternoon|evening|night)|howdy|greetings)[\s!.,?]*$",
    r"^(?:how\s+are\s+you|how'?s\s+it\s+going|how\s+do\s+you\s+do|what'?s\s+up|who\s+are\s+you)[\s!.,?]*$",
    # Friendly discussion / talking about day
    r"\b(?:can\s+we\s+talk\s+about\s+my\s+day|talk\s+about\s+my\s+day|how\s+was\s+your\s+day|let'?s\s+chat|can\s+we\s+chat)\b",
    # Jokes and humor
    r"\b(?:tell\s+me\s+a\s+joke|make\s+me\s+laugh|crack\s+a\s+joke|got\s+any\s+jokes|another\s+joke)\b",
    # Emotional support & personal feelings
    r"\b(?:i\s+had\s+a\s+tiring\s+day|today\s+was\s+a\s+tiring\s+day|tiring\s+day|bad\s+day|feeling\s+(?:sad|down|tired|stressed|exhausted|lonely)|cheer\s+me\s+up|comfort\s+me)\b",
    # Personal memory queries
    r"\b(?:what\s+is\s+my\s+name|who\s+am\s+i|what\s+are\s+my\s+preferences|what\s+do\s+you\s+know\s+about\s+me|remember\s+me)\b",
]

# Stable educational / technical concepts (Category A - Do not search by default)
STABLE_CONCEPT_PATTERNS = [
    r"^explain\s+(?:how|what|why)\s+[a-zA-Z0-9_\s]+(?:\s+works)?$",
    r"^how\s+does\s+[a-zA-Z0-9_\s]+\s+work$",
    r"^(?:what\s+is|what\s+are|define)\s+(?:recursion|photosynthesis|gravity|quantum\s+physics|calculus|oop|inheritance|polymorphism|dna|an\s+atom|the\s+speed\s+of\s+light)[\s?]*$",
    r"^how\s+to\s+(?:write|implement|create|code|learn)\s+[a-zA-Z0-9_\s]+$",
    r"^difference\s+between\s+[a-zA-Z0-9_\s]+\s+and\s+[a-zA-Z0-9_\s]+$",
]

# Current or changing information patterns (Category B - Search required)
CURRENT_INFO_PATTERNS = [
    # News & Breaking
    r"\b(?:happening\s+in\s+the\s+news|in\s+the\s+news\s+today|today'?s\s+news|breaking\s+news|latest\s+news|current\s+headlines|world\s+news\s+today)\b",
    # Software versions & releases
    r"\b(?:latest|current|new)\s+[a-zA-Z0-9_\s\.\+#-]+\s+(?:release|version|update|changelog)\b",
    r"\b(?:latest|current|new)\s+(?:release|version|update|changelog)\s+of\s+[a-zA-Z0-9_\s\.\+#-]+\b",
    r"\b(?:what\s+is\s+the\s+latest\s+[a-zA-Z0-9_\s\.\+#-]+\s+(?:release|version))\b",
    r"\b(?:what\s+is\s+the\s+(?:latest|current)\s+(?:release|version)\s+of\s+[a-zA-Z0-9_\s\.\+#-]+)\b",
    r"\b(?:heard\s+something\s+about\s+a\s+new\s+[a-zA-Z0-9_\s\.\+#-]+\s+release|is\s+there\s+a\s+new\s+[a-zA-Z0-9_\s\.\+#-]+\s+version)\b",
    # Verification of recent news / rumors
    r"\b(?:did\s+.+\s+happen\s+(?:today|recently|yesterday)|is\s+that\s+true\s+about\s+.+|new\s+[a-zA-Z0-9_\s]+release[,\s]+is\s+that\s+true)\b",
    # Live sports, scores & winners
    r"\b(?:who\s+won\s+the\s+match|live\s+score|cricket\s+score|ipl\s+score|football\s+score|match\s+score|world\s+cup\s+winner|tournament\s+results?)\b",
    # Live weather
    r"\b(?:weather\s+today|current\s+weather|forecast\s+for\s+today|temperature\s+right\s+now|weather\s+forecast\s+in)\b",
    # Live market / prices
    r"\b(?:current\s+price\s+of|stock\s+price\s+of|gold\s+rate\s+today|bitcoin\s+price\s+today|crypto\s+prices?)\b",
    # Current public officeholders / leaders
    r"\b(?:who\s+is\s+the\s+current\s+(?:prime\s+minister|president|ceo|governor|leader)\s+of\b|current\s+president\s+of\b|current\s+ceo\s+of\b)",
]


def classify_search_intent(
    query: str,
    conversation_history: Optional[list[dict[str, Any]]] = None
) -> SearchDecision:
    """
    Classifies a user query to determine whether a web search should be executed.
    Prioritizes explicit intent, filters out ordinary conversation and jokes,
    and identifies genuinely time-sensitive or current factual requests.
    """
    cleaned = (query or "").strip()
    if not cleaned:
        return SearchDecision(
            should_search=False,
            category=SearchIntentCategory.NO_SEARCH,
            reason="Empty query."
        )

    lower = cleaned.lower()

    # 1. Negative explicit override: user explicitly asked NOT to search
    for pat in NEGATIVE_SEARCH_PATTERNS:
        if re.search(pat, lower):
            return SearchDecision(
                should_search=False,
                category=SearchIntentCategory.NO_SEARCH,
                reason="Explicit instruction not to search the web."
            )

    # 2. Explicit search requests (Category C)
    for pat, grp_idx in EXPLICIT_SEARCH_PATTERNS:
        m = re.search(pat, cleaned, re.IGNORECASE)
        if m:
            extracted_q = m.group(grp_idx).strip().rstrip("?.!")
            return SearchDecision(
                should_search=True,
                category=SearchIntentCategory.EXPLICIT_SEARCH,
                reason="Explicit user command to search the web or look up online.",
                query=extracted_q or cleaned
            )

    # 3. Check for Ordinary Conversation, Jokes, and Emotional Support (Category A)
    # Important: "Today was a tiring day. Tell me a joke." has "today" casually mentioned,
    # but the intent is emotional/joke. Check ordinary conversation first!
    for pat in ORDINARY_CONVERSATION_PATTERNS:
        if re.search(pat, lower):
            return SearchDecision(
                should_search=False,
                category=SearchIntentCategory.NO_SEARCH,
                reason="Ordinary conversation, greeting, emotional support, or joke request."
            )

    # 4. Check for Stable Educational / Technical Concepts (Category A)
    # Check if user is asking for general stable concept explanation without asking for recency
    has_recency_request = any(
        re.search(pat, lower)
        for pat in [
            r"\b(?:latest|current|new|recent|today|update|release\s+date|version)\b"
        ]
    )
    if not has_recency_request:
        for pat in STABLE_CONCEPT_PATTERNS:
            if re.search(pat, lower):
                return SearchDecision(
                    should_search=False,
                    category=SearchIntentCategory.NO_SEARCH,
                    reason="Stable educational or technical concept explanation."
                )

    # 5. Check Conversation Context: Follow-up discussing already retrieved information
    if conversation_history:
        # Check if the immediate prior messages contain tool results from search
        # and user is asking a conversational follow-up ("tell me more", "summarize that", "why is that")
        recent_msgs = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history
        had_search = any(
            (m.get("role") == "tool" and "results" in m.get("content", ""))
            or (m.get("tool_results") and any(tr.get("tool") in ["search_web", "search_web_tool"] for tr in m.get("tool_results", [])))
            for m in recent_msgs
        )
        if had_search:
            followup_match = re.search(
                r"^(?:tell\s+me\s+more|summarize\s+(?:that|it)|explain\s+(?:that|it)|why\s+did\s+that\s+happen|can\s+you\s+elaborate|what\s+does\s+that\s+mean)\b",
                lower
            )
            # If it's a follow-up discussing already retrieved info without an explicit new search command
            if followup_match and not any(re.search(pat, lower) for pat in [r"\b(?:check\s+again|search\s+again|new\s+updates|verify\s+online)\b"]):
                return SearchDecision(
                    should_search=False,
                    category=SearchIntentCategory.NO_SEARCH,
                    reason="Follow-up discussion of already retrieved search intelligence."
                )

    # 6. Current or Changing Information (Category B - Search required)
    for pat in CURRENT_INFO_PATTERNS:
        if re.search(pat, lower):
            search_q = cleaned.rstrip("?.!")
            # Strip question fluff for search query
            search_q = re.sub(
                r"^(?:what\s+is\s+the|what\s+is|tell\s+me\s+the|tell\s+me\s+about|i\s+heard\s+something\s+about\s+a|is\s+that\s+true\s+about)\s*",
                "",
                search_q,
                flags=re.IGNORECASE
            ).strip()
            return SearchDecision(
                should_search=True,
                category=SearchIntentCategory.SEARCH_REQUIRED,
                reason="Current or changing information request requiring web search.",
                query=search_q or cleaned
            )

    # 7. Fallback / Ambiguous requests:
    # Default to NO_SEARCH for ordinary requests so we don't spam web queries.
    return SearchDecision(
        should_search=False,
        category=SearchIntentCategory.NO_SEARCH,
        reason="Ambiguous or general query with no time-sensitive factual indicators."
    )
