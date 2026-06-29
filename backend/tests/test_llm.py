"""LLM booster client/prompt/parse -- exercised with a fake client (no network)."""

from app.solver.llm import Gap, boost, build_prompt, get_llm_client, parse_answers


class FakeClient:
    """Returns a canned reply and records the prompt it was given."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.prompt = prompt
        return self.reply


GAPS = [
    Gap("1A", "Capital of France", 5, "....."),
    Gap("7D", "Golf goal", 3, "P.."),
]


def test_prompt_includes_clue_length_and_pattern() -> None:
    prompt = build_prompt(GAPS)
    assert "Capital of France" in prompt
    assert "5 letters" in prompt
    assert "P__" in prompt  # '.' rendered as '_' for the model


def test_parse_keeps_valid_and_scores_by_rank() -> None:
    out = parse_answers('{"1A": ["PARIS", "LYONS"], "7D": ["PAR"]}', GAPS)
    assert [w for w, _ in out["1A"]] == ["PARIS", "LYONS"]
    assert out["1A"][0][1] > out["1A"][1][1]  # best-first confidence
    assert out["7D"] == [("PAR", out["7D"][0][1])]
    assert out["7D"][0][1] > 0.6  # a top guess is paint-eligible


def test_parse_filters_wrong_length_pattern_and_nonletters() -> None:
    reply = '{"1A": ["TOOLONGWORD", "lyon", "PA2IS"], "7D": ["CAT", "PAR"]}'
    out = parse_answers(reply, GAPS)
    assert "1A" not in out  # all three are bad: wrong length / wrong length / digit
    assert [w for w, _ in out["7D"]] == ["PAR"]  # CAT fails the "P.." pattern


def test_parse_handles_code_fences_and_junk() -> None:
    fenced = '```json\n{"7D": ["PAR"]}\n```'
    assert parse_answers(fenced, GAPS)["7D"][0][0] == "PAR"
    assert parse_answers("sorry, I cannot help", GAPS) == {}


def test_boost_round_trips_through_a_client() -> None:
    client = FakeClient('{"7D": ["PAR"]}')
    out = boost(GAPS, client)
    assert out == {"7D": [("PAR", out["7D"][0][1])]}
    assert "Golf goal" in (client.prompt or "")


def test_boost_is_safe_when_the_model_errors() -> None:
    class Boom:
        def generate(self, prompt: str) -> str:
            raise ConnectionError("ollama down")

    assert boost(GAPS, Boom()) == {}  # degrades to no extras, never raises


def test_boost_with_no_gaps_skips_the_client() -> None:
    client = FakeClient("should not be called")
    assert boost([], client) == {}
    assert client.prompt is None


def test_disabled_by_default() -> None:
    # No CROSSBOT_LLM env set in the test environment -> booster is off.
    assert get_llm_client() is None
