"""
Regression tests for Search Decision Policy and Web Search Quality.
Tests cover all 12 specified scenarios:
  1. Greeting -> no search
  2. Joke request -> no search
  3. Emotional conversation -> no search
  4. Stable educational question -> no search by default
  5. Current news request -> search
  6. Latest software-version request -> search
  7. Explicit 'search the web' request -> search
  8. Explicit 'do not search' instruction -> no search
  9. Follow-up about already retrieved search results -> no redundant search
  10. Search failure -> honest explanation, no fabricated current facts
  11. Casual mention of 'today' without asking for current facts -> no search
  12. Ambiguous requests -> reasonable default (no unprompted search)
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.app.services.search_decision import (
    classify_search_intent,
    SearchIntentCategory,
    SearchDecision
)
from backend.app.services.chat_service import chat_service
from backend.app.tools.system_tools import search_web_tool


# 1. Greeting -> no search
def test_greeting_no_search():
    greetings = ["Hello", "Hi Jarvis", "Good morning", "Hey", "Howdy!"]
    for g in greetings:
        decision = classify_search_intent(g)
        assert decision.should_search is False, f"Greeting '{g}' triggered search"
        assert decision.category == SearchIntentCategory.NO_SEARCH


# 2. Joke request -> no search
def test_joke_request_no_search():
    joke_queries = [
        "Tell me a joke.",
        "Make me laugh",
        "Got any jokes for me?",
        "Tell me another joke please"
    ]
    for q in joke_queries:
        decision = classify_search_intent(q)
        assert decision.should_search is False, f"Joke request '{q}' triggered search"
        assert decision.category == SearchIntentCategory.NO_SEARCH


# 3. Emotional conversation -> no search
def test_emotional_conversation_no_search():
    emotional_queries = [
        "I am feeling really tired and stressed.",
        "Today was a tiring day. Tell me a joke.",
        "I had a bad day today, comfort me.",
        "Can we talk about my day?",
        "I am feeling lonely tonight."
    ]
    for q in emotional_queries:
        decision = classify_search_intent(q)
        assert decision.should_search is False, f"Emotional query '{q}' triggered search"
        assert decision.category == SearchIntentCategory.NO_SEARCH


# 4. Stable educational question -> no search by default
def test_stable_educational_question_no_search():
    stable_queries = [
        "Explain how Java works.",
        "How does Java work",
        "What is recursion?",
        "Explain photosynthesis",
        "How to write a Python function",
        "Difference between TCP and UDP",
        "What is gravity"
    ]
    for q in stable_queries:
        decision = classify_search_intent(q)
        assert decision.should_search is False, f"Educational query '{q}' triggered search"
        assert decision.category == SearchIntentCategory.NO_SEARCH


# 5. Current news request -> search
def test_current_news_request_search():
    news_queries = [
        "What is happening in the news today?",
        "Breaking news today",
        "Latest news about space exploration",
        "Current headlines",
    ]
    for q in news_queries:
        decision = classify_search_intent(q)
        assert decision.should_search is True, f"News query '{q}' failed to trigger search"
        assert decision.category == SearchIntentCategory.SEARCH_REQUIRED


# 6. Latest software-version request -> search
def test_software_version_request_search():
    version_queries = [
        "What is the latest Java release?",
        "What is the latest Python release?",
        "I heard something about a new Python release. Is that true?",
        "Current version of Node.js",
    ]
    for q in version_queries:
        decision = classify_search_intent(q)
        assert decision.should_search is True, f"Version query '{q}' failed to trigger search"
        assert decision.category == SearchIntentCategory.SEARCH_REQUIRED


# 7. Explicit 'search the web' request -> search
def test_explicit_search_request_search():
    explicit_queries = [
        "Search the web for quantum computing breakthroughs",
        "Search web for latest Mars rover images",
        "Look up the current stock price of Apple",
        "Find recent sources on nuclear fusion",
        "Verify this online: did NASA launch Artemis 2?",
        "Check the latest information about James Webb telescope",
    ]
    for q in explicit_queries:
        decision = classify_search_intent(q)
        assert decision.should_search is True, f"Explicit search '{q}' failed to trigger search"
        assert decision.category == SearchIntentCategory.EXPLICIT_SEARCH
        assert decision.query != ""


# 8. Explicit 'do not search' instruction -> no search
def test_explicit_do_not_search_override():
    no_search_queries = [
        "Answer from your existing knowledge without searching: what is quantum computing?",
        "Do not search the web, tell me what you know about Python.",
        "From your own knowledge without searching, explain gravity.",
        "Don't search, just answer directly."
    ]
    for q in no_search_queries:
        decision = classify_search_intent(q)
        assert decision.should_search is False, f"Negative instruction query '{q}' triggered search"
        assert decision.category == SearchIntentCategory.NO_SEARCH


# 9. Follow-up about already retrieved search results -> no redundant search
def test_followup_on_retrieved_results_no_redundant_search():
    history = [
        {"role": "user", "content": "What is the latest Java release?"},
        {
            "role": "tool",
            "content": '{"success": true, "results": [{"source": "Oracle", "title": "Java 22 Released", "snippet": "Java 22 is out"}]}',
            "tool_results": [{"tool": "search_web_tool", "result": {"success": True}}]
        },
        {"role": "assistant", "content": "According to Oracle, Java 22 is the latest release."}
    ]
    followups = [
        "Can you summarize that in one sentence?",
        "Tell me more about it.",
        "Explain that in simpler terms.",
        "Why did that happen?"
    ]
    for f in followups:
        decision = classify_search_intent(f, conversation_history=history)
        assert decision.should_search is False, f"Follow-up '{f}' triggered redundant search"


# 10. Search failure -> honest explanation, no fabricated facts
def test_search_failure_produces_honest_explanation():
    with patch("httpx.Client") as mock_client:
        mock_instance = MagicMock()
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.post.side_effect = Exception("Network connection timeout")
        mock_client.return_value = mock_instance

        with patch("urllib.request.urlopen", side_effect=Exception("DNS resolution failed")):
            res = search_web_tool("nonexistent topic 9999999")
            assert res["success"] is False
            assert "No live search results could be retrieved" in res["error"]
            assert "could not retrieve verified live results" in res["message"]


# 11. Casual mention of 'today' that does not request current facts -> no search
def test_casual_mention_of_today_no_search():
    casual_today_queries = [
        "Today was a tiring day. Tell me a joke.",
        "I had a lot of coffee today.",
        "Today feels like a great day to learn programming.",
        "What should I cook for dinner today?",
    ]
    for q in casual_today_queries:
        decision = classify_search_intent(q)
        assert decision.should_search is False, f"Casual today query '{q}' triggered search"


# 12. Ambiguous requests -> reasonable default without web spam
def test_ambiguous_requests_reasonable_default():
    ambiguous_queries = [
        "Tell me something interesting.",
        "What do you think?",
        "Can you help me with a problem?",
        "Let's write a story together."
    ]
    for q in ambiguous_queries:
        decision = classify_search_intent(q)
        assert decision.should_search is False, f"Ambiguous query '{q}' triggered search"
        assert decision.category == SearchIntentCategory.NO_SEARCH
