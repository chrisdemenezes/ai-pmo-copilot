from src.agents.shared.output_parser import parse_structured_output


def test_parses_plain_json_object():
    result = parse_structured_output('{"summary": "ok", "decisions": []}')
    assert result == {"structured": True, "summary": "ok", "decisions": []}


def test_parses_json_wrapped_in_markdown_code_fence():
    raw = '```json\n{"summary": "ok"}\n```'
    result = parse_structured_output(raw)
    assert result == {"structured": True, "summary": "ok"}


def test_parses_json_wrapped_in_plain_code_fence():
    raw = '```\n{"summary": "ok"}\n```'
    result = parse_structured_output(raw)
    assert result == {"structured": True, "summary": "ok"}


def test_falls_back_on_invalid_json():
    raw = "This is not JSON at all."
    result = parse_structured_output(raw)
    assert result == {"structured": False, "raw_output": raw}


def test_falls_back_on_non_object_json():
    raw = "[1, 2, 3]"
    result = parse_structured_output(raw)
    assert result == {"structured": False, "raw_output": raw}


def test_falls_back_on_empty_string():
    result = parse_structured_output("")
    assert result == {"structured": False, "raw_output": ""}
