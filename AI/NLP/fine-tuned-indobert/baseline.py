import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import FeatureUnion, Pipeline

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]


def main():
    with open(ROOT / "fine-tuned-indobert" / "configs" / "finetune.yaml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    data_dir = ROOT / cfg["data_dir"]
    with open(data_dir / "dataset_info.json", "r", encoding="utf-8") as f:
        info = json.load(f)
    intent_map = info["intent_map"]
    labels = [intent_map[k] for k in intent_map]

    df = pd.read_parquet(data_dir / "dataset_merged.parquet")

    if "session_id" in df.columns:
        n_folds = df["session_id"].nunique()
        fold_labels = df["session_id"].astype(str)
    else:
        n_folds = 5
        skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=cfg["seed"])
        fold_labels = pd.Series(index=df.index, dtype=str)
        for fold_i, (_, test_idx) in enumerate(skf.split(df["text"], df["intent"])):
            fold_labels.loc[test_idx] = f"fold_{fold_i + 1}"
    sessions = sorted(set(fold_labels))

    pipeline = Pipeline(
        [
            (
                "tfidf",
                FeatureUnion(
                    [
                        ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, lowercase=False)),
                        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)),
                    ]
                ),
            ),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=2000, n_jobs=-1)),
        ]
    )

    rows = []
    for hold in sessions:
        train = df[fold_labels != hold]
        test = df[fold_labels == hold]
        try:
            pipeline.fit(train["text"].astype(str), train["intent"])
        except ValueError:
            pass
        y_pred = pipeline.predict(test["text"].astype(str))
        y_true = test["intent"].map(intent_map).to_numpy()
        y_pred_ids = np.array([intent_map[p] for p in y_pred])
        rep = classification_report(
            y_true, y_pred_ids, labels=list(range(len(labels))),
            target_names=list(intent_map), output_dict=True, zero_division=0,
        )
        rows.append(
            {
                "session": str(hold),
                "n_test": int(len(test)),
                "accuracy": round(float((y_pred_ids == y_true).mean()), 4),
                "macro_f1": round(rep["macro avg"]["f1-score"], 4),
                "weighted_f1": round(rep["weighted avg"]["f1-score"], 4),
            }
        )

    table = pd.DataFrame(rows)
    out = ROOT / "outputs" / "evaluation" / "baseline"
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "summary.csv", index=False, encoding="utf-8-sig")

    mean = {k: round(float(table[k].mean()), 4) for k in ("accuracy", "macro_f1", "weighted_f1")}
    std = {k: round(float(table[k].std()), 4) for k in ("accuracy", "macro_f1", "weighted_f1")}

    cv = json.load(open(ROOT / "outputs" / "evaluation" / "cv" / "summary.json", encoding="utf-8"))
    comparison = {
        "cv_indobert": cv["mean"],
        "cv_indobert_std": cv["std"],
        "baseline_tfidf_logreg": mean,
        "baseline_tfidf_logreg_std": std,
        "delta_accuracy": round(float(mean["accuracy"] - cv["mean"]["accuracy"]), 4),
        "delta_weighted_f1": round(float(mean["weighted_f1"] - cv["mean"]["weighted_f1"]), 4),
    }
    with open(out / "summary.json", "w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)

    print(table.to_string(index=False))
    print("\nbaseline mean ± std:")
    for k in ("accuracy", "macro_f1", "weighted_f1"):
        print(f"  {k:<12}: {mean[k]} ± {std[k]}")
    print("\nperbandingan vs IndoBERT (k-fold sama):")
    for k in ("accuracy", "weighted_f1"):
        print(f"  {k:<12}: baseline {mean[k]} vs indobert {cv['mean'][k]} (delta {comparison['delta_' + k]})")


if __name__ == "__main__":
    main()