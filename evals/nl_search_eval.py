"""
Evaluation harness for PricePulse's natural-language search (Claude -> JSON filters).

What it measures, per test query:
  parsed   the model returned valid JSON (no fallback to plain keyword search needed)
  price    min_price AND max_price both match what a shopper would expect
  keywords the extracted keywords contain at least one expected term
A query passes only if every applicable check passes.

Usage (from the repo root):
    export ANTHROPIC_API_KEY=sk-ant-...
    python -m evals.nl_search_eval                 # real model, writes evals/results/
    python -m evals.nl_search_eval --runs 3        # repeat each query to see run-to-run drift
    python -m evals.nl_search_eval --dry-run       # offline stub, only to test the harness itself

Report the number from a real run on your resume, not from --dry-run.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE / "nl_search_cases.json"
RESULTS = HERE / "results"


def stub_model(system_prompt: str, query: str) -> dict:
    """Crude rule-based stand-in so the harness can be tested without an API key."""
    q = query.lower().replace(",", "").replace("₹", "").replace("rs ", "")

    def num(s):
        m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(k|lakh)?", s.strip())
        if not m:
            return None
        v = float(m.group(1))
        return v * {"k": 1000, "lakh": 100000}.get(m.group(2), 1)

    lo = hi = None
    if m := re.search(r"between (\S+(?: lakh)?) and (\S+)", q):
        lo, hi = num(m.group(1)), num(m.group(2))
    else:
        if m := re.search(r"(?:under|below|less than) (\d+(?:\.\d+)?(?: ?(?:k|lakh))?)", q):
            hi = num(m.group(1))
        if m := re.search(r"(?:above|over|at least) (\d+(?:\.\d+)?(?: ?(?:k|lakh))?)", q):
            lo = num(m.group(1))
    kw = re.sub(r"(under|below|less than|above|over|at least|between|and|for|cheap|best|nice|\d[\d.]*\s?(k|lakh)?|!+)", " ", q)
    return {"keywords": " ".join(kw.split()), "category": None, "min_price": lo, "max_price": hi}


def get_model(dry_run: bool):
    if dry_run:
        return stub_model
    from api.llm_client import call_json
    from api.nl_search import _SYSTEM_PROMPT
    return lambda _sys, query: call_json(_SYSTEM_PROMPT, query)


def same(a, b):
    if a is None or b is None:
        return a is None and b is None
    try:
        return abs(float(a) - float(b)) < 0.01
    except (TypeError, ValueError):
        return False


def evaluate_case(case: dict, model) -> dict:
    out = {"id": case["id"], "query": case["query"], "checks": {}, "output": None, "error": None}
    try:
        data = model(None, case["query"])
        out["output"] = data
        out["checks"]["parsed"] = isinstance(data, dict)
    except ValueError as e:                      # model did not return valid JSON
        out["checks"]["parsed"] = False
        out["error"] = str(e)[:200]
        data = {}
    except Exception as e:                       # network / auth problems: report, don't hide
        out["checks"]["parsed"] = False
        out["error"] = f"{type(e).__name__}: {e}"[:200]
        data = {}

    if not case.get("ambiguous"):
        out["checks"]["price"] = same(data.get("min_price"), case["min_price"]) and same(data.get("max_price"), case["max_price"])
        if case.get("keywords_any"):
            kws = (data.get("keywords") or "").lower()
            out["checks"]["keywords"] = any(t in kws for t in case["keywords_any"])
    out["passed"] = all(out["checks"].values())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="use the offline stub instead of Claude")
    ap.add_argument("--runs", type=int, default=1, help="repeat every query N times")
    args = ap.parse_args()

    cases = json.loads(CASES.read_text(encoding="utf-8"))
    model = get_model(args.dry_run)

    results = []
    for run in range(args.runs):
        for case in cases:
            r = evaluate_case(case, model)
            r["run"] = run + 1
            results.append(r)

    total = len(results)
    passed = sum(r["passed"] for r in results)
    per_check = {}
    for r in results:
        for name, ok in r["checks"].items():
            per_check.setdefault(name, [0, 0])
            per_check[name][0] += ok
            per_check[name][1] += 1

    mode = "DRY RUN (stub, not Claude)" if args.dry_run else "Claude"
    lines = [
        f"# Natural-language search evaluation",
        f"",
        f"- Model: {mode}",
        f"- Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Queries: {len(cases)} x {args.runs} run(s) = {total} checks",
        f"- **Overall pass rate: {passed}/{total} ({100 * passed / total:.0f}%)**",
        f"",
        "| Check | Passed |",
        "|---|---|",
    ]
    for name, (ok, n) in per_check.items():
        lines.append(f"| {name} | {ok}/{n} |")
    failures = [r for r in results if not r["passed"]]
    lines += ["", f"## Failures ({len(failures)})", ""]
    for r in failures:
        failed = [k for k, v in r["checks"].items() if not v]
        lines.append(f"- #{r['id']} `{r['query']}` failed: {', '.join(failed)}. Output: `{json.dumps(r['output'])}` {r['error'] or ''}")
    report = "\n".join(lines) + "\n"

    RESULTS.mkdir(exist_ok=True)
    suffix = "dry_run" if args.dry_run else "claude"
    (RESULTS / f"nl_search_{suffix}.md").write_text(report, encoding="utf-8")
    (RESULTS / f"nl_search_{suffix}.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
