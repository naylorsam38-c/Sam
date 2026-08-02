from aura.phrasing import PhraseChunker, MIN_WORDS, MAX_WORDS


def test_phrases_bounded_word_count():
    c = PhraseChunker()
    text = ("Here is what I found today, and it is quite interesting; "
            "the results are clear and the numbers add up nicely.")
    out = []
    for tok in text.split(" "):
        out += c.feed(tok + " ")
    rest = c.flush()
    if rest:
        out.append(rest)
    assert out, "should emit phrases"
    for p in out[:-1]:                    # last (flush) may be short
        assert MIN_WORDS <= len(p.split()) <= MAX_WORDS, p


def test_short_input_waits_for_flush():
    c = PhraseChunker()
    assert c.feed("just three words") == []
    assert c.flush() == "just three words"


def test_boundary_cut_on_punctuation():
    c = PhraseChunker()
    got = c.feed("hello there my friend, ")
    assert any("," in g for g in got)
