"""Ask Jev how well each sentence of a doc is backed by evidence, and draw a report.

Run from the project root (needs the TYPESAFE_API_KEY environment variable):

    python -I scripts/checks/jev_evidence_report.py docs/comparing-with-the-game.md

Writes reports/jev-evidence-<doc>.html (gitignored). Answers are cached in
reports/jev-cache.json, so running the same doc again costs nothing.

What it sends to api.typesafe.ai: the doc's own prose, one paragraph at a
time (headings, code blocks and indented command lines are left out), plus
the paragraph before it for context. Do not point it at a file that quotes
game text or assets (CLAUDE.md, hard rule 1).

Jev's labels are its opinion. "Backed" means the text cites evidence, not
that the evidence is true.
"""
import hashlib
import html
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
CACHE_FILE = REPORTS / "jev-cache.json"
URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
UNSURE_BELOW = 0.6
MAX_QUESTIONS = 25
WORKERS = 4

CRITERIA = {
    "backed": "The sentence or its nearby text cites evidence: a run, check script, count, date or code read.",
    "marked_uncertain": "The sentence itself says it is inferred, guessed, not tested, unknown or not checked.",
    "unbacked": "A factual statement with no evidence cited in the sentence or nearby text.",
    "not_a_claim": "Not a factual claim: instruction, plan, command, question, label or description of the doc.",
}
LABELS = {
    "backed": "Backed",
    "marked_uncertain": "Marked as unsure",
    "unbacked": "Not backed",
    "not_a_claim": "Not a claim",
    "unsure": "Jev unsure",
}
ORDER = ["backed", "marked_uncertain", "unbacked", "not_a_claim", "unsure"]


# --- reading the doc -------------------------------------------------------

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(.*)$")
TABLE_SEP = re.compile(r"^\|[\s\-:|]+\|$")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[*`\"(A-Z])")


def read_blocks(text):
    """Split markdown into prose blocks: {section, units}. One unit is a
    paragraph, a list item or a table row."""
    blocks = []
    path = []
    cur = None
    in_fence = False
    prev_blank = True
    prev_code = False

    def flush():
        nonlocal cur
        if cur and cur["units"]:
            blocks.append(cur)
        cur = None

    def start(kind):
        nonlocal cur
        flush()
        cur = {"kind": kind, "section": " > ".join(path), "units": []}

    for raw in text.split("\n"):
        line = raw.rstrip()
        if line.startswith("```"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line.strip():
            flush()
            prev_blank, prev_code = True, False
            continue
        m = HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            path[:] = path[: level - 1] + [m.group(2).strip()]
            prev_blank, prev_code = False, False
            continue
        if line.startswith("    ") and (prev_blank or prev_code) and cur is None:
            prev_blank, prev_code = False, True
            continue
        prev_blank, prev_code = False, False
        if line.startswith("|"):
            if cur is None or cur["kind"] != "table":
                start("table")
            if TABLE_SEP.match(line):
                if len(cur["units"]) == 1:
                    cur["units"] = []  # the row before the separator was the header
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            cur["units"].append(" - ".join(c for c in cells if c))
            continue
        m = LIST_ITEM.match(line)
        if m:
            if cur is None or cur["kind"] != "list":
                start("list")
            cur["units"].append(m.group(1).strip())
            continue
        if cur is None:
            start("para")
            cur["units"].append(line.strip())
        else:
            cur["units"][-1] += " " + line.strip()
    flush()
    return blocks


def split_sentences(unit):
    out = []
    for s in SENTENCE_END.split(unit):
        s = s.strip()
        if len(s.split()) >= 3 and len(s) >= 12:
            out.append(s)
    return out


# --- asking Jev ------------------------------------------------------------

_cache_lock = threading.Lock()
_usage = {"input": 0, "output": 0, "calls": 0, "cached": 0}


def load_cache():
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ask(body, cache):
    payload = json.dumps(body, ensure_ascii=False)
    key = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    with _cache_lock:
        if key in cache:
            _usage["cached"] += 1
            return cache[key]
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        sys.exit("TYPESAFE_API_KEY is not set")
    delay = 2
    for attempt in range(6):
        req = urllib.request.Request(
            URL,
            data=payload.encode("utf-8"),
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            if e.code in (429, 529) or e.code >= 500:
                time.sleep(delay)
                delay *= 2
                continue
            sys.exit("Jev returned %d: %s" % (e.code, detail))
        except (urllib.error.URLError, TimeoutError):
            time.sleep(delay)
            delay *= 2
    else:
        sys.exit("Jev did not answer after 6 tries")
    with _cache_lock:
        cache[key] = result
        _usage["calls"] += 1
        u = result.get("usage", {})
        _usage["input"] += u.get("input_tokens", 0)
        _usage["output"] += u.get("output_tokens", 0)
        REPORTS.mkdir(exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    return result


def judge(doc_name, blocks, cache):
    """Return one record per sentence, in document order."""
    jobs = []
    prev_text = ""
    for b in blocks:
        text = "\n".join(b["units"])
        sentences = [s for u in b["units"] for s in split_sentences(u)]
        for i in range(0, len(sentences), MAX_QUESTIONS):
            chunk = sentences[i : i + MAX_QUESTIONS]
            body = {
                "model": MODEL,
                "state": {
                    "document": doc_name,
                    "section": b["section"],
                    "previous_text": prev_text[-700:],
                    "text": text,
                },
                "questions": {
                    "s%d" % n: {
                        "type": "choice",
                        "instructions": 'How well is this sentence of the text backed by evidence? Sentence: "%s"' % s,
                        "criteria": CRITERIA,
                    }
                    for n, s in enumerate(chunk)
                },
            }
            jobs.append((b["section"], chunk, body))
        prev_text = text

    with ThreadPoolExecutor(WORKERS) as pool:
        results = list(pool.map(lambda j: ask(j[2], cache), jobs))

    records = []
    for (section, chunk, _), result in zip(jobs, results):
        for n, s in enumerate(chunk):
            a = result["answers"]["s%d" % n]
            conf = a.get("confidence") or 0.0
            choice = a["choice"]
            records.append(
                {
                    "section": section,
                    "sentence": s,
                    "choice": choice,
                    "confidence": conf,
                    "category": choice if conf >= UNSURE_BELOW else "unsure",
                    "probabilities": a.get("probabilities", {}),
                }
            )
    return records


# --- the report ------------------------------------------------------------

CSS = """
:root{--bg:#fbfaf8;--fg:#1f2328;--muted:#656d76;--line:#d8d6d0;--card:#fff;
--backed:#2a7f62;--marked_uncertain:#c98a1a;--unbacked:#c0392b;--not_a_claim:#8a8f98;--unsure:#6b5ca5}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#17181a;--fg:#e6e6e3;--muted:#a0a4ab;--line:#33363a;--card:#1f2124;
--backed:#4fb596;--marked_uncertain:#e0aa4a;--unbacked:#e5705f;--not_a_claim:#8c919a;--unsure:#9a8fd1}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,Segoe UI,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:32px 0 10px}
.sub{color:var(--muted);margin:0 0 18px}
.note{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;color:var(--muted);font-size:14px}
.bar{display:flex;height:34px;border-radius:6px;overflow:hidden;border:1px solid var(--line)}
.bar.small{height:16px}
.seg{display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;font-weight:600;min-width:0;overflow:hidden}
.seg.unsure{background-image:repeating-linear-gradient(45deg,rgba(255,255,255,.28) 0 4px,transparent 4px 8px)}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;margin:12px 0}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block}
.sec{display:grid;grid-template-columns:minmax(0,1fr) 240px 70px;gap:12px;align-items:center;padding:7px 0;border-bottom:1px solid var(--line)}
.sec .name{font-size:14px;overflow-wrap:anywhere}.sec .pct{color:var(--muted);font-size:13px;text-align:right}
.filters{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 14px}
.filters button{font:inherit;font-size:13px;padding:5px 11px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
.filters button[aria-pressed=true]{background:var(--fg);color:var(--bg)}
.item{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--c);border-radius:6px;padding:9px 12px;margin:8px 0}
.item .meta{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12px;color:var(--muted);margin-top:4px}
.chip{font-weight:700;color:var(--c)}
code{font:13px Consolas,monospace;background:rgba(127,127,127,.15);padding:0 4px;border-radius:3px}
@media (max-width:640px){.sec{grid-template-columns:1fr}.sec .pct{text-align:left}}
"""


def fmt(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def bar(counts, small=False):
    total = sum(counts.values()) or 1
    segs = []
    for cat in ORDER:
        n = counts.get(cat, 0)
        if not n:
            continue
        pct = 100.0 * n / total
        label = str(n) if pct >= 6 and not small else ""
        segs.append(
            '<div class="seg %s" style="width:%.2f%%;background-color:var(--%s)" title="%s: %d">%s</div>'
            % (cat, pct, cat, LABELS[cat], n, label)
        )
    return '<div class="bar%s">%s</div>' % (" small" if small else "", "".join(segs))


def count(records):
    c = {}
    for r in records:
        c[r["category"]] = c.get(r["category"], 0) + 1
    return c


def write_report(doc_path, records, out_path):
    total = count(records)
    n = len(records)
    legend = "".join(
        '<span><i class="sw" style="background:var(--%s)"></i>%s <b>%d</b></span>'
        % (cat, LABELS[cat], total.get(cat, 0))
        for cat in ORDER
    )
    claims = sum(total.get(c, 0) for c in ("backed", "marked_uncertain", "unbacked", "unsure"))
    backed_pct = 100.0 * total.get("backed", 0) / claims if claims else 0.0

    sections = []
    for r in records:
        if not sections or sections[-1][0] != r["section"]:
            sections.append((r["section"], []))
        sections[-1][1].append(r)
    sec_rows = []
    for name, recs in sections:
        c = count(recs)
        cl = sum(c.get(k, 0) for k in ("backed", "marked_uncertain", "unbacked", "unsure"))
        pct = "%d%% backed" % round(100.0 * c.get("backed", 0) / cl) if cl else "no claims"
        short = html.escape(name.split(" > ")[-1] or "(top of the doc)")
        sec_rows.append(
            '<div class="sec"><div class="name">%s</div>%s<div class="pct">%s</div></div>'
            % (short, bar(c, small=True), pct)
        )

    buttons = ['<button data-f="all" aria-pressed="false">All (%d)</button>' % n]
    for cat in ORDER:
        pressed = "true" if cat == "unbacked" else "false"
        buttons.append(
            '<button data-f="%s" aria-pressed="%s">%s (%d)</button>' % (cat, pressed, LABELS[cat], total.get(cat, 0))
        )
    items = []
    for r in records:
        lean = ""
        if r["category"] == "unsure":
            lean = " &middot; leaning %s" % LABELS.get(r["choice"], r["choice"])
        probs = ", ".join("%s %.0f%%" % (LABELS.get(k, k), 100 * v) for k, v in r["probabilities"].items())
        items.append(
            '<div class="item" data-cat="%s" style="--c:var(--%s)"><div>%s</div>'
            '<div class="meta"><span class="chip">%s</span><span>confidence %.0f%%%s</span>'
            '<span title="%s">%s</span></div></div>'
            % (
                r["category"],
                r["category"],
                fmt(r["sentence"]),
                LABELS[r["category"]],
                100 * r["confidence"],
                lean,
                html.escape(probs),
                html.escape(r["section"].split(" > ")[-1]),
            )
        )

    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Evidence report</title>
<style>%s</style></head><body><main>
<h1>How well is each sentence backed by evidence?</h1>
<p class="sub">%s &middot; %d sentences &middot; made %s</p>
<div class="note">These labels are Jev's opinion and were not checked by hand. "Backed" means the text
cites a run, a check script, a count or a code read. It does not mean the claim is true.
"Jev unsure" means its confidence was under %d%%.</div>
<h2>The whole doc</h2>
%s<div class="legend">%s</div>
<p class="sub">Of the %d sentences that make a claim, %.0f%% are labelled backed.</p>
<h2>By section</h2>%s
<h2>The sentences</h2>
<div class="filters">%s</div>
<div id="list">%s</div>
</main><script>
const btns=[...document.querySelectorAll('.filters button')];
function show(f){btns.forEach(b=>b.setAttribute('aria-pressed',b.dataset.f===f));
document.querySelectorAll('.item').forEach(i=>i.hidden=!(f==='all'||i.dataset.cat===f));}
btns.forEach(b=>b.onclick=()=>show(b.dataset.f));show('unbacked');
</script></body></html>""" % (
        CSS,
        html.escape(doc_path.name),
        n,
        time.strftime("%Y-%m-%d"),
        int(UNSURE_BELOW * 100),
        bar(total),
        legend,
        claims,
        backed_pct,
        "".join(sec_rows),
        "".join(buttons),
        "".join(items),
    )
    out_path.write_text(page, encoding="utf-8")


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python -I scripts/checks/jev_evidence_report.py docs/<doc>.md")
    doc = Path(sys.argv[1]).resolve()
    text = doc.read_text(encoding="utf-8")
    blocks = read_blocks(text)
    cache = load_cache()
    records = judge(doc.name, blocks, cache)
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / ("jev-evidence-%s.html" % doc.stem)
    write_report(doc, records, out)
    print("sentences judged:", len(records))
    print("by label:", count(records))
    print("Jev calls: %(calls)d new, %(cached)d from cache" % _usage)
    print("tokens billed this run: %(input)d in, %(output)d out" % _usage)
    print("report:", out)


if __name__ == "__main__":
    main()
