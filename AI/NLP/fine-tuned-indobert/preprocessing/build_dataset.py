import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight

ROOT = Path(__file__).resolve().parents[2]

VALID_INTENTS = {
    "product_inquiry", "size_inquiry", "size_recommendation", "color_inquiry",
    "price_inquiry", "stock_availability", "purchase_intent", "not_relevant",
}
VALID_SENTIMENTS = {"positive", "neutral", "negative"}


def load_csv(path: Path):
    rows = []
    with open(path, encoding="utf-8") as f:
        content = f.read()
        if content.startswith("\ufeff"):
            content = content[1:]
        for row in csv.DictReader(content.splitlines()):
            rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "fine-tuned-indobert" / "configs" / "finetune.yaml"))
    ap.add_argument("--src", default=str(ROOT / "data" / "dataset" / "merged_10k.csv"))
    ap.add_argument("--val-frac", type=float, default=0.10)
    ap.add_argument("--test-frac", type=float, default=0.10)
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    seed = cfg["seed"]

    with open(ROOT / "fine-tuned-indobert" / "configs" / "taxonomy.yaml", "r", encoding="utf-8") as f:
        taxonomy = yaml.safe_load(f)
    intent_map = {i["id"]: i["label_id"] for i in taxonomy["intents"]}
    sentiment_map = {s["id"]: s["label_id"] for s in taxonomy["sentiments"]}

    out_dir = ROOT / cfg["data_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = load_csv(Path(args.src))
    df = pd.DataFrame(rows)[["comment_id", "text", "intent", "sentiment"]]
    df = df.drop_duplicates(subset="comment_id").reset_index(drop=True)

    bad_intent = set(df["intent"]) - VALID_INTENTS
    bad_sent = set(df["sentiment"]) - VALID_SENTIMENTS
    if bad_intent or bad_sent:
        raise SystemExit(f"label tidak dikenal: intents={bad_intent} sentiments={bad_sent}")

    train, tmp = train_test_split(
        df, test_size=args.val_frac + args.test_frac,
        stratify=df["intent"], random_state=seed,
    )
    val, test = train_test_split(
        tmp, test_size=args.test_frac / (args.val_frac + args.test_frac),
        stratify=tmp["intent"], random_state=seed + 1,
    )
    train = train.reset_index(drop=True).sort_values("comment_id")
    val = val.reset_index(drop=True).sort_values("comment_id")
    test = test.reset_index(drop=True).sort_values("comment_id")

    weights = compute_class_weight(
        "balanced", classes=np.unique(train["intent"]), y=train["intent"]
    )
    class_weights = {
        k: round(float(v), 3)
        for k, v in zip(np.unique(train["intent"]), weights)
    }

    for name, part in [("train", train), ("val", val), ("test", test)]:
        part.to_csv(out_dir / f"{name}.csv", index=False, encoding="utf-8-sig")

    pd.concat([train, val, test], ignore_index=True).to_parquet(
        out_dir / "dataset_merged.parquet", index=False
    )

    info = {
        "method": "stratified_row_wise",
        "split_seed": seed,
        "val_frac": args.val_frac,
        "test_frac": args.test_frac,
        "n_total": int(len(df)),
        "n_train": int(len(train)),
        "n_val": int(len(val)),
        "n_test": int(len(test)),
        "has_session_id": False,
        "intent_map": intent_map,
        "sentiment_map": sentiment_map,
        "class_weights": class_weights,
        "counts": {"train": int(len(train)), "val": int(len(val)), "test": int(len(test))},
    }
    with open(out_dir / "dataset_info.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print(f"total        : {len(df)}")
    print(f"train/val/test: {len(train)} / {len(val)} / {len(test)}")
    print("\nkomposisi per split (intent):")
    all_parts = pd.concat(
        [train.assign(split="train"), val.assign(split="val"), test.assign(split="test")],
        ignore_index=True,
    )
    print(pd.crosstab(all_parts["intent"], all_parts["split"]).to_string())
    print("\nclass_weights (train):")
    for k, v in class_weights.items():
        print(f"  {k:<20}: {v}")
    print("\noutput:", out_dir)


if __name__ == "__main__":
    main()