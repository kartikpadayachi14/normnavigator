from pathlib import Path

import pytest

from normnavigator.ingest.eurlex import SPLIT_POINTS_MIN_CHARS, parse_file

FIXTURE = Path(__file__).parent / "fixtures" / "mini_eurlex.html"
RAW = Path(__file__).parents[1] / "data" / "raw"


@pytest.fixture
def chunks(tmp_path):
    # Inflate the definitions so Article 3 crosses the point-split threshold.
    filler = "x" * (SPLIT_POINTS_MIN_CHARS // 2)
    html = FIXTURE.read_text(encoding="utf-8").replace("LONG_FILLER", filler)
    f = tmp_path / "mini.html"
    f.write_text(html, encoding="utf-8")
    return {c.chunk_id: c for c in parse_file(f, "2023/1230", "en")}


def test_paragraph_articles_become_one_chunk_per_paragraph(chunks):
    p1, p2 = chunks["2023/1230:en:art10:p1"], chunks["2023/1230:en:art10:p2"]
    assert p1.title == "Obligations of manufacturers of machinery and related products"
    assert "\xa0" not in p1.text and "(7)" not in p1.text  # nbsp + footnote marker removed
    assert p2.text.splitlines() == [
        "2. Manufacturers shall draw up the technical documentation set out in Annex IV.",
        "They shall affix the CE marking in accordance with Article 24.",
    ]


def test_short_list_article_stays_whole_with_rows_joined(chunks):
    c = chunks["2023/1230:en:art2"]
    assert c.text == "This Regulation applies to:\n(a) machinery;\n(b) related products."


def test_long_list_article_split_per_point_with_lead_in(chunks):
    c = chunks["2023/1230:en:art3:pt2"]
    assert c.point == "2"
    assert c.text.startswith("For the purposes of this Regulation, the following definitions")
    assert "'risk' means" in c.text and "'AI system'" not in c.text


def test_annexes_ignored(chunks):
    assert all(":art" in cid for cid in chunks)
    assert len(chunks) == 5


SOURCES = {"2023/1230": "mr_2023_1230", "2024/1689": "aia_2024_1689", "2023/988": "gpsr_2023_988"}


@pytest.mark.parametrize("reg,stem", SOURCES.items())
def test_real_files_de_en_parity(reg, stem):
    """German and English texts are parallel, so they must yield identical chunk structure."""
    en_f, de_f = RAW / f"{stem}_en.html", RAW / f"{stem}_de.html"
    if not (en_f.exists() and de_f.exists()):
        pytest.skip("raw EUR-Lex files not present (not committed)")
    en = {c.chunk_id.replace(":en:", ":") for c in parse_file(en_f, reg, "en")}
    de = {c.chunk_id.replace(":de:", ":") for c in parse_file(de_f, reg, "de")}
    assert en == de
    assert len(en) > 100
