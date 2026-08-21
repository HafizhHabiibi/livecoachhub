import json
import re
import string
from collections import Counter
from pathlib import Path

import emoji

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "dataset_stats"

EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF]")


def main():
    texts = []
    for f in sorted(Path(ROOT / "data" / "raw").glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("type") == "comment" and rec.get("text"):
                texts.append(rec["text"])

    n_words = [len(t.split()) for t in texts]
    uniq = set(t.strip().lower() for t in texts)
    has_emoji = [1 if EMOJI_RE.search(t) else 0 for t in texts]
    ends_q = [1 if t.rstrip().endswith("?") or t.rstrip().endswith("？？") else 0 for t in texts]

    def pct(feats):
        return round(100 * sum(feats) / len(feats), 1)

    buckets = {
        "1-2 kata (sangat pendek)": sum(1 for w in n_words if w <= 2),
        "3-6 kata (pendek)": sum(1 for w in n_words if 3 <= w <= 6),
        "7-11 kata (medium)": sum(1 for w in n_words if 7 <= w <= 11),
        "12+ kata (panjang)": sum(1 for w in n_words if w >= 12),
    }

    lower_all = [t.lower() for t in texts]
    greets = {k: sum(1 for t in lower_all if k in t.split()) for k in ("kak", "ka", "kaka", "min", "kak?")}
    neg = {k: sum(1 for t in lower_all if k in t.split()) for k in ("gak", "ga", "nggak", "gk", "engga")}
    tokens = [w for t in lower_all for w in re.findall(r"[a-z0-9]+", t)]
    top = Counter(tokens).most_common(40)
    numbers = [t for t in texts if re.search(r"\b(bb|tb|ld|lp|kg|cm|rb|k)\b", t.lower())]
    question_markers = sum(1 for t in lower_all if "berap" in t or "brp" in t or "?size" in t)

    stats = {
        "n_comment": len(texts),
        "n_unique_text": len(uniq),
        "word_mean": round(sum(n_words) / len(n_words), 2),
        "word_median": sorted(n_words)[len(n_words) // 2],
        "len_buckets_pct": {k: round(100 * v / len(texts), 1) for k, v in buckets.items()},
        "emoji_pct": pct(has_emoji),
        "question_mark_pct": pct(ends_q),
        "greeting_variants": greets,
        "negation_variants": neg,
        "top_40_words": dict(top),
        "body_metric_comments": len(numbers),
        "body_metric_pct": round(100 * len(numbers) / len(texts), 1),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "style_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()