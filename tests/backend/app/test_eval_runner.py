from scripts.run_eval import score_case


def test_score_case_passes_for_fallback_report():
    case = {
        "id": "fallback-case",
        "chat_history": [
            {
                "role": "user",
                "content": "I have chest pain and trouble breathing.",
            }
        ],
        "expected_summary_contains": ["chest pain", "trouble breathing"],
        "requires_urgent_language": True,
    }

    result = score_case(case)

    assert result["score"] == result["max_score"]
    assert result["checks"]["urgent_language"] is True
