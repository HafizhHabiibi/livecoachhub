import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import classification_report, confusion_matrix
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="run1")
    args = ap.parse_args()

    data_dir = ROOT / "data" / "processed" / "indobert_dataset"
    model_dir = ROOT / "fine-tuned-indobert" / "outputs" / "models" / "indobert-intent" / args.run / "best"
    out_dir = ROOT / "fine-tuned-indobert" / "outputs" / "evaluation" / args.run
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(data_dir / "dataset_info.json", "r", encoding="utf-8") as f:
        info = json.load(f)
    intent_map = info["intent_map"]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).to(device)
    model.eval()

    test_df = pd.read_csv(data_dir / "test.csv", encoding="utf-8-sig")
    texts = test_df["text"].astype(str).tolist()
    y_true = test_df["intent"].map(intent_map).to_numpy()
    test_sessions = (
        [str(s) for s in test_df["session_id"].unique()]
        if "session_id" in test_df.columns
        else ["row-based split (tanpa session)"]
    )

    all_logits = []
    for i in range(0, len(texts), 32):
        batch = texts[i:i + 32]
        enc = tokenizer(batch, padding=True, truncation=True, max_length=64, return_tensors="pt").to(device)
        with torch.no_grad():
            all_logits.append(model(**enc).logits.cpu().numpy())
    logits = np.concatenate(all_logits)
    y_pred = logits.argmax(axis=-1)
    probs = torch.softmax(torch.from_numpy(logits), dim=-1).numpy()

    id2label = {v: k for k, v in intent_map.items()}
    labels = [id2label[i] for i in range(len(intent_map))]

    acc = float((y_pred == y_true).mean())
    rep = classification_report(y_true, y_pred, labels=list(range(len(labels))),
                                target_names=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(labels))))

    report_df = pd.DataFrame(rep).T.reset_index(names="class")
    cm_df = pd.DataFrame(cm, index=labels, columns=pd.Index(labels, name="predicted"))

    report_df.to_csv(out_dir / "classification_report.csv", index=False, encoding="utf-8-sig")
    cm_df.to_csv(out_dir / "confusion_matrix.csv", encoding="utf-8-sig")

    test_out = test_df.copy()
    test_out["label_id_true"] = y_true
    test_out["label_id_pred"] = y_pred
    test_out["pred_intent"] = [id2label[i] for i in y_pred]
    test_out["confidence"] = probs.max(axis=-1)
    test_out.to_csv(out_dir / "test_predictions.csv", index=False, encoding="utf-8-sig")

    summary = {
        "run": args.run,
        "test_samples": int(len(test_df)),
        "test_sessions": test_sessions,
        "accuracy": round(acc, 4),
        "macro_f1": round(rep["macro avg"]["f1-score"], 4),
        "weighted_f1": round(rep["weighted avg"]["f1-score"], 4),
        "per_class_f1": {k: round(v["f1-score"], 4) for k, v in rep.items()
                         if isinstance(v, dict) and k in labels},
    }
    with open(out_dir / "report.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    n_test_sessions = len(test_sessions)
    print(f"test samples : {len(test_df)} ({n_test_sessions} session)")
    print(f"accuracy     : {acc:.4f}")
    print(f"macro F1     : {summary['macro_f1']}")
    print(f"weighted F1  : {summary['weighted_f1']}")
    print("per-class F1 :")
    for k, v in summary["per_class_f1"].items():
        print(f"  {k:<18}: {v}")
    print("output       :", out_dir)


if __name__ == "__main__":
    main()