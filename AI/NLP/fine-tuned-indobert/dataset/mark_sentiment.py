import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "dataset" / "gen" / "raw"

POS_TARGET = 0.027
NEG_TARGET = 0.023
SEED = 42

MARKER = re.compile(r"\s*\|\s*(pos|neg)\s*$", re.IGNORECASE)


def main():
    rng = random.Random(SEED)
    total = 0
    for path in sorted(RAW.glob("*.txt")):
        lines = [ln.rstrip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        clean = [MARKER.sub("", ln).rstrip() for ln in lines]
        n = len(clean)
        total += n
        n_pos = round(n * POS_TARGET)
        n_neg = round(n * NEG_TARGET)
        pool = list(range(n))
        rng.shuffle(pool)
        pos_idx = set(pool[:n_pos])
        neg_idx = set(pool[n_pos: n_pos + n_neg])
        out = []
        for i, ln in enumerate(clean):
            if i in pos_idx:
                ln = f"{ln} | pos"
            elif i in neg_idx:
                ln = f"{ln} | neg"
            out.append(ln)
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"{path.name}: +{n_pos} pos, +{n_neg} neg")
    print("total lines:", total)


if __name__ == "__main__":
    main()