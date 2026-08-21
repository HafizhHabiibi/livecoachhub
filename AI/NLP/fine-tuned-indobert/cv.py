import argparse
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold
from sklearn.utils.class_weight import compute_class_weight
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)

from ml.train import TorchDictDataset, WeightedLossTrainer

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "fine-tuned-indobert" / "configs" / "finetune.yaml"))
    ap.add_argument("--output", default=str(ROOT / "outputs" / "evaluation" / "cv"))
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    data_dir = ROOT / cfg["data_dir"]
    with open(data_dir / "dataset_info.json", "r", encoding="utf-8") as f:
        info = json.load(f)
    intent_map = info["intent_map"]

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
    labels = [intent_map[k] for k in intent_map]
    id2label = {v: k for k, v in intent_map.items()}

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(cfg["model"])
    folds = []
    agg_cm = np.zeros((len(labels), len(labels)), dtype=int)

    for i, hold in enumerate(sessions, 1):
        train_df = df[fold_labels != hold].reset_index(drop=True)
        test_df = df[fold_labels == hold].reset_index(drop=True)

        max_length = cfg["max_length"]
        batch_size = cfg["batch_size"]

        def tokenize(d):
            texts = d["text"].astype(str).tolist()
            lbl = d["intent"].map(intent_map).astype(int).tolist()
            enc = tokenizer(texts, padding="max_length", truncation=True, max_length=max_length)
            enc["labels"] = lbl
            return TorchDictDataset({k: torch.tensor(v) for k, v in enc.items()})

        train_ds, test_ds = tokenize(train_df), tokenize(test_df)

        vocab = sorted(intent_map)
        w_arr = compute_class_weight("balanced", classes=np.unique(train_df["intent"]), y=train_df["intent"])
        w_dict = dict(zip(np.unique(train_df["intent"]), w_arr))
        weights = np.array([w_dict.get(v, 1.0) for v in vocab], dtype=np.float32)

        steps_per_epoch = math.ceil(len(train_df) / (batch_size * cfg.get("gradient_accumulation_steps", 1)))
        warmup_steps = int(cfg["warmup_ratio"] * steps_per_epoch * cfg["epochs"])

        model = AutoModelForSequenceClassification.from_pretrained(
            cfg["model"], num_labels=len(intent_map), id2label=id2label, label2id=intent_map
        )

        ckpt = out_dir / f"fold_{i}_ckpt"
        training_args = TrainingArguments(
            output_dir=str(ckpt),
            num_train_epochs=cfg["epochs"],
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            gradient_accumulation_steps=cfg.get("gradient_accumulation_steps", 1),
            learning_rate=cfg["learning_rate"],
            weight_decay=cfg["weight_decay"],
            warmup_steps=warmup_steps,
            fp16=cfg["fp16"],
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="eval_loss",
            save_total_limit=1,
            seed=cfg["seed"],
            logging_steps=50,
            report_to=[],
            dataloader_pin_memory=False,
        )

        trainer = WeightedLossTrainer(
            class_weights=weights,
            model=model,
            args=training_args,
            train_dataset=train_ds,
            eval_dataset=test_ds,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=cfg["early_stopping_patience"])],
        )
        trainer.train()
        shutil.rmtree(ckpt, ignore_errors=True)

        device = trainer.args.device
        y_true = test_df["intent"].map(intent_map).to_numpy()
        all_logits = []
        for j in range(0, len(test_df), 32):
            enc = tokenizer(
                test_df["text"].astype(str).tolist()[j:j + 32],
                padding=True, truncation=True, max_length=max_length, return_tensors="pt",
            ).to(device)
            with torch.no_grad():
                all_logits.append(trainer.model(**enc).logits.cpu().numpy())
        y_pred = np.concatenate(all_logits).argmax(axis=-1)

        rep = classification_report(y_true, y_pred, labels=list(range(len(labels))),
                                    target_names=labels, output_dict=True, zero_division=0)
        cm = confusion_matrix(y_true, y_pred, labels=list(range(len(labels))))
        fold_id = str(hold)

        fold = {
            "fold": i,
            "session": fold_id,
            "n_train": int(len(train_df)),
            "n_test": int(len(test_df)),
            "accuracy": round(float((y_pred == y_true).mean()), 4),
            "macro_f1": round(rep["macro avg"]["f1-score"], 4),
            "weighted_f1": round(rep["weighted avg"]["f1-score"], 4),
            "per_class_f1": {k: round(v["f1-score"], 4) for k, v in rep.items()
                             if isinstance(v, dict) and k in labels},
        }
        folds.append(fold)

        cm_df = pd.DataFrame(cm, index=labels, columns=pd.Index(labels, name="predicted"))
        cm_df.to_csv(out_dir / f"fold_{i}_confusion.csv", encoding="utf-8-sig")

        agg_cm += cm

        print(f"fold {i:>2}/{len(sessions)} | holdout={fold_id[:8]} | "
              f"acc={fold['accuracy']:.4f} macro={fold['macro_f1']:.4f} wf1={fold['weighted_f1']:.4f} | "
              f"train {fold['n_train']} test {fold['n_test']}")

    pd.DataFrame(agg_cm, index=labels, columns=pd.Index(labels, name="predicted")).to_csv(
        out_dir / "aggregated_confusion.csv", encoding="utf-8-sig"
    )

    with open(out_dir / "folds.json", "w", encoding="utf-8") as f:
        json.dump({"sessions": sessions, "folds": folds}, f, ensure_ascii=False, indent=2)

    agg_sum = pd.DataFrame(
        {
            k: [fd[k] for fd in folds]
            for k in ("fold", "session", "n_train", "n_test", "accuracy", "macro_f1", "weighted_f1")
        }
    )
    agg_sum.to_csv(out_dir / "summary.csv", index=False, encoding="utf-8-sig")

    mean = {k: round(float(agg_sum[k].mean()), 4) for k in ("accuracy", "macro_f1", "weighted_f1")}
    std = {k: round(float(agg_sum[k].std()), 4) for k in ("accuracy", "macro_f1", "weighted_f1")}
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump({"n_folds": len(folds), "mean": mean, "std": std}, f, ensure_ascii=False, indent=2)

    print("\n=== ringkasan k-fold ===")
    print(agg_sum.to_string(index=False))
    print("mean ± std:")
    for k in ("accuracy", "macro_f1", "weighted_f1"):
        print(f"  {k:<12}: {mean[k]} ± {std[k]}")


if __name__ == "__main__":
    main()