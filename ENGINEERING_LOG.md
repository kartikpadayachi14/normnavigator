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

## RISKS

| Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|
| Source HTML/models unreachable from dev sandbox | High (happened) | Medium | Run downloads and model inference on user machine or in CI; allowlist domains if plan permits | Open |
| EUR-Lex HTML structure differs between regulations | Medium | Medium | Write parser against real files; snapshot tests per regulation | Open |
| Test set labelled by LLM is biased toward its own retrieval | Medium | High | LLM only drafts; every question + gold article verified by hand; labelling method documented | Open |
| LLM API cost during evaluation | Medium | Low | Log tokens per call; cache judge outputs; small dev subset | Open |
| Azure student credits run out / deployment cost | Low | Medium | Container Apps scale-to-zero; small image; teardown script | Open |
| Leaked secrets in commits | Low | High | `.env` gitignored, `.env.example` placeholders, secret grep before every commit | Mitigated |
