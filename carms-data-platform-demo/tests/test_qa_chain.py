from src.qa.qa_chain import _strip_meta_commentary


def test_strip_meta_commentary_leading_phrase():
    answer = "According to the provided context, the following documents are required:\n\n1. X\n2. Y"
    assert _strip_meta_commentary(answer) == "The following documents are required:\n\n1. X\n2. Y"


def test_strip_meta_commentary_mid_sentence():
    answer = (
        "The documents required vary by program. However, based on the provided "
        "information, the following documents are mentioned as being required:\n\n- X"
    )
    assert _strip_meta_commentary(answer) == (
        "The documents required vary by program. However, the following documents "
        "are mentioned as being required:\n\n- X"
    )


def test_strip_meta_commentary_no_match_is_unchanged():
    answer = "You simply need X and Y."
    assert _strip_meta_commentary(answer) == answer
