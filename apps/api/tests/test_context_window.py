from app.services.context_window import count_message_tokens, manage_history


def test_trim_preserves_system_and_newest_messages():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "old question " * 20},
        {"role": "assistant", "content": "old answer " * 20},
        {"role": "user", "content": "new question"},
    ]
    result = manage_history(
        messages,
        context_limit=40,
        reserved_output_tokens=5,
        safety_margin_tokens=5,
    )

    assert result.messages[0]["role"] == "system"
    assert result.messages[-1]["content"] == "new question"
    assert result.removed_messages > 0
    assert result.fits_budget


def test_summarize_replaces_old_history():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "first question " * 20},
        {"role": "assistant", "content": "first answer " * 20},
        {"role": "user", "content": "current question"},
    ]
    result = manage_history(
        messages,
        context_limit=30,
        reserved_output_tokens=5,
        safety_margin_tokens=5,
        strategy="summarize",
        summarizer=lambda old: "The user asked about the first topic.",
    )

    assert result.summarized_messages == 2
    assert result.summary_message is not None
    assert "Conversation summary:" in result.summary_message["content"]
    assert result.fits_budget


def test_history_token_count_is_non_negative():
    assert count_message_tokens([]) == 0
