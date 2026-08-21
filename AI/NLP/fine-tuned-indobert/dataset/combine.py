import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "dataset" / "gen" / "raw"
OUT = ROOT / "data" / "dataset" / "gen" / "all_generated.csv"

MARKER = re.compile(r"\s*\|\s*(pos|neg)\s*$", re.IGNORECASE)


def load_batch(path: Path):
    with open(path, encoding="utf-8") as f:
        lines = [ln.rstrip("\n").rstrip() for ln in f if ln.strip()]
    rows = []
    for ln in lines:
        m = MARKER.search(ln)
        if m:
            text = ln[: m.start()].rstrip()
            sentiment = "positive" if m.group(1).lower() == "pos" else "negative"
        else:
            text = ln
            sentiment = "neutral"
        rows.append((text, sentiment))
    return rows


def main():
    all_rows = []
    seen = set()
    for path in sorted(RAW.glob("*.txt")):
        intent = path.stem.rsplit("_b", 1)[0]
        for text, sentiment in load_batch(path):
            if text in seen:
                raise SystemExit(f"duplicate line in {path.name}: {text}")
            seen.add(text)
            all_rows.append((len(all_rows) + 1, text, intent, sentiment))

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["comment_id", "text", "intent", "sentiment"])
        for i, text, intent, sentiment in all_rows:
            w.writerow([f"gen_{i:05d}", text, intent, sentiment])

    print("total:", len(all_rows))
    print("per intent:")
    counts = {}
    for _, _, intent, _ in all_rows:
        counts[intent] = counts.get(intent, 0) + 1
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print("per sentiment:")
    sc = {}
    for _, _, _, s in all_rows:
        sc[s] = sc.get(s, 0) + 1
    for k, v in sc.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
