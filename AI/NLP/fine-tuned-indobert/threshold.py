import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="run1")
    args = ap.parse_args()
    OUT = ROOT / "fine-tuned-indobert" / "outputs" / "evaluation" / args.run

    df = pd.read_csv(OUT / "test_predictions.csv", encoding="utf-8-sig")
    y_true = df["intent"].tolist()
    y_pred = df["pred_intent"].tolist()
    conf = df["confidence"].to_numpy()
    labels = sorted(set(y_true) | set(y_pred))

    rows = []
    for thr in [0.0, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
        n_remap = int((conf < thr).sum())
        pred = [p if c >= thr else "other" for p, c in zip(y_pred, conf)]
        rows.append(
            {
                "threshold": round(thr, 2),
                "accuracy": round(float((np.array(pred) == np.array(y_true)).mean()), 4),
                "macro_f1": round(f1_score(y_true, pred, labels=labels, average="macro", zero_division=0), 4),
                "weighted_f1": round(f1_score(y_true, pred, labels=labels, average="weighted", zero_division=0), 4),
                "n_remapped": n_remap,
                "coverage": round(float(1 - n_remap / len(df)), 4),
            }
        )

    table = pd.DataFrame(rows)
    table.to_csv(OUT / "threshold.csv", index=False, encoding="utf-8-sig")

    best = table.loc[table["weighted_f1"].idxmax()]
    recommendation = {
        "metric": "weighted_f1",
        "threshold": float(best["threshold"]),
        "weighted_f1": float(best["weighted_f1"]),
        "accuracy": float(best["accuracy"]),
        "coverage": float(best["coverage"]),
    }
    with open(OUT / "threshold.json", "w", encoding="utf-8") as f:
        json.dump({"table": rows, "recommendation": recommendation}, f, ensure_ascii=False, indent=2)

    plt.figure(figsize=(6, 4))
    plt.plot(table["threshold"], table["accuracy"], marker="o", label="accuracy")
    plt.plot(table["threshold"], table["macro_f1"], marker="s", label="macro F1")
    plt.plot(table["threshold"], table["weighted_f1"], marker="^", label="weighted F1")
    plt.axvline(best["threshold"], color="gray", linestyle="--", linewidth=1)
    plt.xlabel("threshold (skor < threshold -> other)")
    plt.ylabel("skor")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT / "threshold_curve.png", dpi=150)
    plt.close()

    print(table.to_string(index=False))
    print("\nrekomendasi (max weighted F1):", recommendation)


if __name__ == "__main__":
    main()