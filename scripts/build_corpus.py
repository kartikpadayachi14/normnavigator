"""Parse the six EUR-Lex HTML files into chunks.

Usage:  python scripts/build_corpus.py [--raw data/raw] [--out data/processed/chunks.jsonl]

Writes:
  data/processed/chunks.jsonl   one JSON chunk per line (gitignored, rebuilt by this script)
  results/corpus_stats.json     counts, length stats, DE/EN parity, source SHA-256 hashes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from datetime import UTC, datetime
from pathlib import Path

from normnavigator.ingest.eurlex import parse_file

SOURCES = {
    "2023/1230": "mr_2023_1230",  # Machinery Regulation
    "2024/1689": "aia_2024_1689",  # AI Act
    "2023/988": "gpsr_2023_988",  # General Product Safety Regulation
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/processed/chunks.jsonl")
    ap.add_argument("--stats", default="results/corpus_stats.json")
    args = ap.parse_args()

    raw, out = Path(args.raw), Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stats: dict = {"generated_at": datetime.now(UTC).isoformat(), "regulations": {}}
    total = 0
    with out.open("w", encoding="utf-8") as fh:
        for reg, stem in SOURCES.items():
            per_lang, ids = {}, {}
            for lang in ("en", "de"):
                path = raw / f"{stem}_{lang}.html"
                chunks = parse_file(path, reg, lang)
                for c in chunks:
                    fh.write(json.dumps({"chunk_id": c.chunk_id, **c.model_dump()}) + "\n")
                lengths = [len(c.text) for c in chunks]
                ids[lang] = {c.chunk_id.replace(f":{lang}:", ":") for c in chunks}
                per_lang[lang] = {
                    "source_file": path.name,
                    "source_sha256": sha256(path),
                    "chunks": len(chunks),
                    "articles": len({c.article for c in chunks}),
                    "point_split_chunks": sum(1 for c in chunks if c.point),
                    "chars_min": min(lengths),
                    "chars_median": statistics.median(lengths),
                    "chars_max": max(lengths),
                }
                total += len(chunks)
            per_lang["parity_only_en"] = sorted(ids["en"] - ids["de"])
            per_lang["parity_only_de"] = sorted(ids["de"] - ids["en"])
            stats["regulations"][reg] = per_lang
    stats["total_chunks"] = total
    Path(args.stats).parent.mkdir(parents=True, exist_ok=True)
    Path(args.stats).write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {total} chunks -> {out}; stats -> {args.stats}")


if __name__ == "__main__":
    main()
