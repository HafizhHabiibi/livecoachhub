import csv
import re
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[2]
GEN_CSV = ROOT / "data" / "dataset" / "gen" / "all_generated.csv"
ORIG = ROOT / "data" / "dataset" / "relabel_draft.csv"
OUT = ROOT / "data" / "dataset" / "merged_10k.csv"

TARGET_PER_INTENT = 1250
JACCARD_THRESHOLD = 0.95


def norm(text: str) -> str:
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def four_grams(s: str):
    s = " " + s + " "
    return {s[i : i + 4] for i in range(len(s) - 3)}


def jaccard(a: str, b: str) -> float:
    ga, gb = four_grams(a), four_grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def load_csv(path: Path, intent_col: str = "intent"):
    rows = []
    with open(path, encoding="utf-8") as f:
        content = f.read()
        if content.startswith("\ufeff"):
            content = content[1:]
        r = csv.DictReader(content.splitlines())
        for row in r:
            if intent_col in row:
                row["intent"] = row.pop(intent_col)
            rows.append(row)
    return rows


class GramIndex:
    def __init__(self):
        self._idx = defaultdict(list)

    def add(self, grams, text_idx):
        for g in grams:
            self._idx[g].append(text_idx)

    def candidates(self, grams):
        ids = set()
        for g in grams:
            ids.update(self._idx[g])
        return ids


def main():
    gen = load_csv(GEN_CSV)
    orig = load_csv(ORIG, intent_col="intent_baru")

    orig_norm = [norm(row["text"]) for row in orig]
    seen_norm = {n: i for i, n in enumerate(orig_norm)}
    orig_idx = GramIndex()
    for i, n in enumerate(orig_norm):
        orig_idx.add(four_grams(n), i)

    kept = []
    removed = {"vs_ori": 0, "vs_gen": 0}
    gen_norm_list = []
    gen_idx = GramIndex()

    def near_dup(target, index, norm_list):
        gs = four_grams(target)
        ln = len(target)
        cand = index.candidates(gs)
        for i in cand:
            other = norm_list[i]
            if abs(len(other) - ln) > max(4, ln // 4):
                continue
            if jaccard(target, other) >= JACCARD_THRESHOLD:
                return True
        return False

    for row in tqdm(gen, desc="dedupe 4-gram", unit="baris"):
        text = row["text"]
        n = norm(text)
        if n in seen_norm:
            removed["vs_ori"] += 1
            continue
        if near_dup(n, orig_idx, orig_norm):
            removed["vs_ori"] += 1
            continue
        if near_dup(n, gen_idx, gen_norm_list):
            removed["vs_gen"] += 1
            continue
        seen_norm[n] = len(gen_norm_list)
        gen_norm_list.append(n)
        gen_idx.add(four_grams(n), len(gen_norm_list) - 1)
        kept.append(row)

    counts = {}
    for row in kept:
        counts[row["intent"]] = counts.get(row["intent"], 0) + 1
    total = len(gen) + len(orig)
    print("baris hasil pengembangan diterima:", len(kept))
    print("dibuang vs asli:", removed["vs_ori"])
    print("dibuang near-dup:", removed["vs_gen"])
    print("per intent hasil pengembangan:")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")

    merged = orig + kept
    merged_by_intent = {}
    for row in merged:
        merged_by_intent.setdefault(row["intent"], []).append(row)

    final = []
    for intent, rows in merged_by_intent.items():
        if len(rows) > TARGET_PER_INTENT:
            rows = rows[:TARGET_PER_INTENT]
        elif len(rows) < TARGET_PER_INTENT:
            print(f"PERINGATAN: {intent} cuma {len(rows)} (target {TARGET_PER_INTENT})")
        final.extend(rows)

    final.sort(key=lambda r: r["comment_id"])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["comment_id", "text", "intent", "sentiment"])
        for row in final:
            w.writerow([row["comment_id"], row["text"], row["intent"], row["sentiment"]])

    print("final total:", len(final))
    sc = {}
    for row in final:
        sc[row["sentiment"]] = sc.get(row["sentiment"], 0) + 1
    for k, v in sorted(sc.items()):
        print(f"  sentiment {k}: {v}")


if __name__ == "__main__":
    main()