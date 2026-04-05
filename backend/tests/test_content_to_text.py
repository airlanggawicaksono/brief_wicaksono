from app.services.predict.steps import _content_to_text


def test_plain_string():
    assert _content_to_text("  hello  ") == "hello"


def test_empty_string():
    assert _content_to_text("") == ""


def test_list_of_strings():
    assert _content_to_text(["hello", "world"]) == "hello world"


def test_list_of_dicts_with_text_key():
    assert _content_to_text([{"text": "hello"}, {"text": "world"}]) == "hello world"


def test_list_mixed_strings_and_dicts():
    assert _content_to_text(["hello", {"text": "world"}]) == "hello world"


def test_list_with_empty_entries_stripped():
    assert _content_to_text(["hello", "", "  ", {"text": "world"}]) == "hello world"


def test_dict_without_text_key_ignored():
    assert _content_to_text([{"type": "image", "url": "..."}]) == ""


def test_unsupported_type_returns_empty():
    assert _content_to_text(None) == ""
    assert _content_to_text(123) == ""
