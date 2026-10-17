import pytest
from src.domain.multilingual_lexicon import MultilingualLexicon


def test_lexicon_expands_thai_box_to_english_and_japanese():
    lexicon = MultilingualLexicon()
    synonyms = lexicon.expand_terms("กล่อง")
    assert "box" in synonyms
    assert "箱" in synonyms
    assert "ボックス" in synonyms
    assert "botton box" in synonyms or "button box" in synonyms


def test_lexicon_expands_japanese_box_to_english_and_thai():
    lexicon = MultilingualLexicon()
    synonyms_kanji = lexicon.expand_terms("箱")
    assert "box" in synonyms_kanji
    assert "กล่อง" in synonyms_kanji

    synonyms_katakana = lexicon.expand_terms("ボックス")
    assert "box" in synonyms_katakana
    assert "กล่อง" in synonyms_katakana


def test_lexicon_expands_japanese_belt():
    lexicon = MultilingualLexicon()
    synonyms = lexicon.expand_terms("ベルト")
    assert "belt" in synonyms
    assert "สายพาน" in synonyms
    assert "v-belt" in synonyms


def test_lexicon_expands_quotation():
    lexicon = MultilingualLexicon()
    synonyms_jp = lexicon.expand_terms("見積書")
    assert "quotation" in synonyms_jp
    assert "ใบเสนอราคา" in synonyms_jp

    synonyms_thai = lexicon.expand_terms("ใบเสนอราคา")
    assert "quotation" in synonyms_thai
    assert "見積" in synonyms_thai or "見積書" in synonyms_thai


def test_lexicon_does_not_over_expand_short_tokens_or_fragments():
    lexicon = MultilingualLexicon()
    s_synonyms = lexicon.expand_terms("s")
    assert "box" not in s_synonyms
    assert "箱" not in s_synonyms
    assert s_synonyms == {"s"}

    a_synonyms = lexicon.expand_terms("a")
    assert "valve" not in a_synonyms
    assert a_synonyms == {"a"}


def test_lexicon_expands_thai_container_panchana_to_box():
    """Tests semantic hypernym discovery: 'ภาชนะ' (container/receptacle) -> box / enclosure."""
    lexicon = MultilingualLexicon()
    synonyms = lexicon.expand_terms("ภาชนะ")
    assert "box" in synonyms
    assert "container" in synonyms
    assert "กล่อง" in synonyms
    assert "箱" in synonyms
