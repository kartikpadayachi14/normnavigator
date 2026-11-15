# Engineering Log — NormNavigator

Tags: [MEASURED] = produced by a script in this repo · [IMPLEMENTED] = in code, not measured · [PLANNED] = not done.

---

## 2026-11-15 — Session 1: scaffold + data-independent core (Milestone 1, part 1)

**Goal:** Set up the repo and build the parts of retrieval/evaluation that do not need the
regulation texts yet: chunk data model, score fusion, retrieval metrics, tests, CI.

**What was built**
- `src/normnavigator/schema.py` — `Chunk` model (one chunk = one paragraph of one article in one language), `chunk_id` (e.g. `2023/1230:de:art18:p2`), `article_key` (language-independent, e.g. `2023/1230:art18`). [IMPLEMENTED]
- `src/normnavigator/retrieval/fusion.py` — `reciprocal_rank_fusion()` (RRF, k=60) and `weighted_fusion()` (min-max normalised, alpha-weighted). [IMPLEMENTED]
- `src/normnavigator/eval/metrics.py` — `dedupe_to_articles()`, `hit_at_k()`, `reciprocal_rank()` (mean = MRR), `recall_at_k()`. [IMPLEMENTED]
- `tests/test_fusion.py`, `tests/test_metrics.py` — 12 unit tests with hand-computed expected values. [IMPLEMENTED]
- `.github/workflows/ci.yml` — ruff lint + format check + pytest on push/PR. [IMPLEMENTED, not yet run on GitHub]
- `.gitignore`, `.env.example`, pinned `requirements*.txt`, `pyproject.toml`, README with Mermaid diagram.

**Decisions and why**
| Decision | Alternatives considered | Why |
|---|---|---|
| Chunk by article paragraph | Fixed 512-token windows; whole articles | Maps 1:1 to legal citations ("Art. 18(2)"); whole articles can be very long and dilute embeddings |
| Gold labels at article level, language-independent | Paragraph-level labels; per-language labels | Paragraph labels are slow and ambiguous to make by hand; language-independent labels let a DE query hitting the EN article count, which is the cross-lingual ability we want to measure |
| De-duplicate retrieved chunks to articles before ranking | Rank raw chunks | Otherwise several paragraphs of one wrong article push the right one down and distort hit@k/MRR |
| Implement both RRF and weighted fusion | Only one | The evaluation should *show* which works better on this corpus, not assume it |
| Deterministic tie-break (score, then id) | Python's default ordering | Evaluation runs must be reproducible |
| ruff for lint+format | flake8 + black + isort | One fast tool, one config |

**Problems hit**
- Workspace network blocks `eur-lex.europa.eu` and `huggingface.co` (proxy `connect_rejected`). Root cause: sandbox egress allowlist. Impact: cannot download regulation texts or embedding models here. Mitigation: build data-independent parts first; options for the data recorded under Next steps.
- ruff E501 (2 lines > 100 chars). Fix: `ruff format .`.

**Commands and key outputs**
```
pytest -q            -> 12 passed
ruff check .         -> All checks passed!
```

**Metrics this session:** none (no data yet). All README metrics are NOT MEASURED.

**Next steps**
1. Get the six source files (3 regulations × DE/EN HTML from EUR-Lex) into `data/raw/` — via domain allowlisting, the user's machine, or attachment.
2. Write the EUR-Lex parser against the *real* HTML and test it on real snippets.
3. BM25 + multilingual embedding indexes; retrieval eval script writing `results/retrieval_eval.json`.
4. Push to GitHub and confirm CI runs green.

---

## 2026-11-15 — Session 2: EUR-Lex parser + corpus build (Milestone 1, part 2)

**Goal:** Parse the six real source files (3 regulations × DE/EN) into citation-level chunks.

**What was built**
- Source files supplied by user (saved from EUR-Lex in the browser), copied to `data/raw/` as `{mr_2023_1230,aia_2024_1689,gpsr_2023_988}_{en,de}.html`. SHA-256 of each recorded in `results/corpus_stats.json`.
- `src/normnavigator/ingest/eurlex.py` — `parse_file()`, `parse_article()`, `block_text()`. [IMPLEMENTED]
- `schema.Chunk` gained an optional `point` field; ids like `2024/1689:en:art3:pt12`.
- `scripts/build_corpus.py` — writes `data/processed/chunks.jsonl` and `results/corpus_stats.json`. [MEASURED]
- `tests/test_eurlex_parser.py` + `tests/fixtures/mini_eurlex.html` (trimmed real structure) — 4 fixture tests (run in CI) + 3 real-file DE/EN parity tests (skipped when raw files are absent, e.g. in CI).

**How the HTML is structured (checked on the real files, not assumed)**
- Each article: `<div class="eli-subdivision" id="art_N">`, heading `p.oj-ti-art`, title `p.oj-sti-art`.
- Numbered paragraphs: child `<div id="010.002">` = article 10, paragraph 2.
- Articles without numbered paragraphs (e.g. AI Act Art. 3 definitions): lead-in `<p>` + one `<table>` per enumerated point.
- Footnote markers: `.oj-note-tag`; non-breaking spaces after paragraph numbers.

**Decisions and why**
| Decision | Alternatives | Why |
|---|---|---|
| Split long list-articles (>2000 chars) per point, prefix lead-in sentence | Keep whole article; split every list | AI Act Art. 3 has 68 definitions — one chunk would bury every definition; short lists like "Scope (a)(b)" read better whole. Lead-in keeps each point a complete statement ("For the purposes of this Regulation… 'provider' means…") |
| Join cells of one table row on one line | Plain `get_text()` | Keeps "(a) machinery;" together instead of "(a)\nmachinery;" |
| Remove footnote markers | Keep | "(7)" markers are noise for BM25 and look like point numbers |
| Skip annexes for now | Parse them too | Annex structure is irregular; articles are enough for the first evaluation. Machinery Annex III (essential requirements) matters → open issue |
| Use DE/EN parity as the correctness check | Manual spot checks only | The two texts are official parallel versions, so identical chunk ids in both languages is strong automatic evidence the parser does not drop or merge paragraphs |

**Problems hit**
- `ModuleNotFoundError: normnavigator` when running scripts. Root cause: src-layout package not installed. Fix: `pip install -e .`.
- Edit to `schema.py` rejected because ruff had reformatted the file after it was last read. Fix: re-read, re-apply.

**Commands and key outputs**
```
python scripts/build_corpus.py  -> wrote 2134 chunks -> data/processed/chunks.jsonl
pytest -q                       -> 19 passed
```

**Metrics this session** (source: `results/corpus_stats.json`) [MEASURED]
| Regulation | Articles | Chunks per language | Point-split chunks | DE/EN parity mismatches |
|---|---|---|---|---|
| 2023/1230 Machinery | 54 | 239 | 36 | 0 |
| 2024/1689 AI Act | 113 | 605 | 89 | 0 |
| 2023/988 GPSR | 52 | 223 | 30 | 0 |
| **Total** | 219 | 1067 (2134 both languages) | 155 | 0 |

**Open issues / next steps**
- Push to GitHub blocked: Claude GitHub App not installed for the repo (push check refused). Needs user action.
- Annexes not parsed (esp. Machinery Annex III).
- Longest chunk 5578 chars (AI Act Art. 5(1), DE). Fine for BM25 and bge-m3 (8192-token limit); check if smaller embedding models truncate.
- Milestone 2: BM25 index, embedding index (model download must run where huggingface.co is reachable), labelled test set.

---

## RISKS

| Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|
| Source HTML/models unreachable from dev sandbox | High (happened) | Medium | Run downloads and model inference on user machine or in CI; allowlist domains if plan permits | Open |
| EUR-Lex HTML structure differs between regulations | Medium | Medium | Parser written against all six real files; DE/EN parity test per regulation (0 mismatches) | Mitigated |
| Raw files saved via browser may differ from a script download (consolidated versions, converter versions differ: EN MR 9.15 vs DE 9.16) | Medium | Low | SHA-256 of every source in `results/corpus_stats.json`; parity test catches structural drift | Open |
| Annexes excluded → questions about essential requirements unanswerable | High | Medium | Test set limited to article content for v1; annex parsing planned | Open |
| Test set labelled by LLM is biased toward its own retrieval | Medium | High | LLM only drafts; every question + gold article verified by hand; labelling method documented | Open |
| LLM API cost during evaluation | Medium | Low | Log tokens per call; cache judge outputs; small dev subset | Open |
| Azure student credits run out / deployment cost | Low | Medium | Container Apps scale-to-zero; small image; teardown script | Open |
| Leaked secrets in commits | Low | High | `.env` gitignored, `.env.example` placeholders, secret grep before every commit | Mitigated |
