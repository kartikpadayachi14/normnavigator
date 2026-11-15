"""Parser for EUR-Lex HTML (Official Journal "CONVEX" format, checked on converter 9.15–9.16).

Structure observed in the real files (see tests/fixtures for trimmed copies):

    <div class="eli-subdivision" id="art_10">
      <p class="oj-ti-art">Article 10</p>
      <div class="eli-title"><p class="oj-sti-art">Obligations of manufacturers ...</p></div>
      <div id="010.001"><p class="oj-normal">1.   When placing ...</p></div>   <- paragraph 1
      <div id="010.002"> ... </div>                                            <- paragraph 2

Articles without numbered paragraphs (e.g. AI Act Art. 3, definitions) instead contain a
lead-in <p> followed by one <table> per enumerated point ("1." | "'AI system' means ...").

Chunking rule:
  * numbered paragraph divs present -> one chunk per paragraph
  * otherwise, if the article is long and has enumerated tables -> one chunk per point,
    each prefixed with the lead-in sentence so it still reads as a complete statement
  * otherwise -> one chunk for the whole article

Annexes are NOT parsed yet (they are less regular). Recorded as an open issue.
"""

from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from normnavigator.schema import Chunk, Lang

ARTICLE_ID = re.compile(r"^art_(\d+[a-z]?)$")
PARAGRAPH_ID = re.compile(r"^(\d{3})\.(\d{3})$")
TEXT_CLASSES = {"oj-normal", "oj-tbl-txt"}
SPLIT_POINTS_MIN_CHARS = 2000  # below this, a list article stays one chunk


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def block_text(el: Tag) -> str:
    """Flatten an element to text: cells of one table row on one line, other <p> on own lines."""
    lines: list[str] = []
    last_row: Tag | None = None
    for p in el.find_all("p"):
        if not TEXT_CLASSES.intersection(p.get("class") or []):
            continue
        t = _clean(p.get_text(" "))
        if not t:
            continue
        row = p.find_parent("tr")
        if row is not None and row is last_row and lines:
            lines[-1] = f"{lines[-1]} {t}"
        else:
            lines.append(t)
        last_row = row
    return "\n".join(lines)


def _strip_footnote_markers(soup: BeautifulSoup) -> None:
    for tag in soup.select(".oj-note-tag"):
        tag.decompose()


def parse_article(div: Tag, regulation: str, lang: Lang) -> list[Chunk]:
    m = ARTICLE_ID.match(div.get("id", ""))
    if not m:
        raise ValueError(f"Not an article div: {div.get('id')!r}")
    article = m.group(1)
    sti = div.find("p", class_="oj-sti-art")
    title = _clean(sti.get_text(" ")) if sti else ""
    base = {"regulation": regulation, "lang": lang, "article": article, "title": title}

    para_divs = [
        c for c in div.find_all("div", recursive=False) if PARAGRAPH_ID.match(c.get("id", ""))
    ]
    if para_divs:
        chunks = []
        for pd in para_divs:
            pnum = str(int(PARAGRAPH_ID.match(pd["id"]).group(2)))
            text = block_text(pd)
            if text:
                chunks.append(Chunk(**base, paragraph=pnum, text=text))
        return chunks

    # No numbered paragraphs: lead-in text + enumerated top-level tables?
    lead_parts, tables = [], []
    for child in div.find_all(recursive=False):
        classes = child.get("class") or []
        if child.name == "table":
            tables.append(child)
        elif child.name == "p" and "oj-normal" in classes and not tables:
            lead_parts.append(_clean(child.get_text(" ")))
    whole = block_text(div)
    if tables and len(whole) > SPLIT_POINTS_MIN_CHARS:
        lead = " ".join(lead_parts)
        chunks = []
        for i, tbl in enumerate(tables, start=1):
            body = block_text(tbl)
            first = tbl.find("p", class_="oj-normal")
            label = _clean(first.get_text(" ")).rstrip(".()") if first else str(i)
            label = label.strip("()") or str(i)
            chunks.append(Chunk(**base, point=label, text=f"{lead}\n{body}" if lead else body))
        return chunks
    return [Chunk(**base, text=whole)] if whole else []


def parse_file(path: str | Path, regulation: str, lang: Lang) -> list[Chunk]:
    html = Path(path).read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")
    _strip_footnote_markers(soup)
    chunks: list[Chunk] = []
    for div in soup.find_all("div", id=ARTICLE_ID):
        chunks.extend(parse_article(div, regulation, lang))
    return chunks
