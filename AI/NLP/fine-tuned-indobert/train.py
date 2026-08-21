import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from torch import nn
from torch.utils.data import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    EarlyStoppingCallback,
    Trainer,
    TrainingArguments,
)

ROOT = Path(__file__).resolve().parents[1]


class TorchDictDataset(Dataset):
    def __init__(self, tensors):
        self.tensors = tensors
        self.n = len(tensors["labels"])

    def __len__(self):
        return self.n

    def __getitem__(self, idx):
        return {k: v[idx] for k, v in self.tensors.items()}


class WeightedLossTrainer(Trainer):
    def __init__(self, class_weights, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loss_fn = nn.CrossEntropyLoss(
            weight=torch.tensor(class_weights, dtype=torch.float32, device=self.args.device)
        )

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=0):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        loss = self.loss_fn(logits.view(-1, self.model.config.num_labels), labels.view(-1))
        return (loss, outputs) if return_outputs else loss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "fine-tuned-indobert" / "configs" / "finetune.yaml"))
    ap.add_argument("--run", default="run1")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    data_dir = ROOT / cfg["data_dir"]
    out_dir = ROOT / cfg["output_dir"] / args.run
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(data_dir / "dataset_info.json", "r", encoding="utf-8") as f:
        info = json.load(f)
    intent_map = info["intent_map"]

    train_df = pd.read_csv(data_dir / "train.csv", encoding="utf-8-sig")
    val_df = pd.read_csv(data_dir / "val.csv", encoding="utf-8-sig")
    n_labels = len(intent_map)

    tokenizer = AutoTokenizer.from_pretrained(cfg["model"])
    id2label = {v: k for k, v in intent_map.items()}
    model = AutoModelForSequenceClassification.from_pretrained(
        cfg["model"], num_labels=n_labels, id2label=id2label, label2id=intent_map
    )

    def tokenize(df):
        texts = df["text"].astype(str).tolist()
        labels = df["intent"].map(intent_map).astype(int).tolist()
        enc = tokenizer(
            texts, padding="max_length", truncation=True, max_length=cfg["max_length"]
        )
        enc["labels"] = labels
        return TorchDictDataset({k: torch.tensor(v) for k, v in enc.items()})

    train_ds, val_ds = tokenize(train_df), tokenize(val_df)

    steps_per_epoch = math.ceil(len(train_df) / (cfg["batch_size"] * cfg.get("gradient_accumulation_steps", 1)))
    warmup_steps = int(cfg["warmup_ratio"] * steps_per_epoch * cfg["epochs"])

    weights = np.array([info["class_weights"][name] for name in intent_map], dtype=np.float32)

    training_args = TrainingArguments(
        output_dir=str(out_dir),
        num_train_epochs=cfg["epochs"],
        per_device_train_batch_size=cfg["batch_size"],
        per_device_eval_batch_size=cfg["batch_size"],
        gradient_accumulation_steps=cfg.get("gradient_accumulation_steps", 1),
        learning_rate=cfg["learning_rate"],
        weight_decay=cfg["weight_decay"],
        warmup_steps=warmup_steps,
        fp16=cfg["fp16"],
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        save_total_limit=2,
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
        eval_dataset=val_ds,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=cfg["early_stopping_patience"])],
    )

    trainer.train()
    trainer.save_model(str(out_dir / "best"))
    tokenizer.save_pretrained(str(out_dir / "best"))

    with open(out_dir / "train_meta.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "run": args.run,
                "model": cfg["model"],
                "num_labels": n_labels,
                "intent_map": intent_map,
                "trained_samples": len(train_df),
                "val_samples": len(val_df),
                "best_metric": trainer.state.best_metric,
                "config": cfg,
            },
            f, ensure_ascii=False, indent=2,
        )
    print("selesai. best eval_loss:", trainer.state.best_metric)
    print("checkpoint terbaik  :", out_dir / "best")


if __name__ == "__main__":
    main()