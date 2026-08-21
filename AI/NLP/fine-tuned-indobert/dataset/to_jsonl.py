import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "dataset" / "merged_10k.csv"
OUT = ROOT / "data" / "dataset" / "tiktok_live_10k.jsonl"


def main():
    with open(SRC, encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)

    with open(OUT, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("written:", OUT)
    print("total:", len(rows))


if __name__ == "__main__":
    main()