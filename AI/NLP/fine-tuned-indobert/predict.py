import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]


def load_model(run="run1"):
    model_dir = ROOT / "fine-tuned-indobert" / "outputs" / "models" / "indobert-intent" / run / "best"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).to(device)
    model.eval()
    return model, tokenizer, device


def predict(texts, model, tokenizer, device, batch_size=32, max_length=64):
    texts = [str(t) for t in texts]
    all_logits = []
    for i in range(0, len(texts), batch_size):
        enc = tokenizer(texts[i:i + batch_size], padding=True, truncation=True,
                        max_length=max_length, return_tensors="pt").to(device)
        with torch.no_grad():
            all_logits.append(model(**enc).logits.cpu().numpy())
    logits = np.concatenate(all_logits)
    probs = torch.softmax(torch.from_numpy(logits), dim=-1).numpy()
    label_ids = probs.argmax(axis=-1)
    id2label = model.config.id2label
    return [id2label[int(i)] for i in label_ids], probs.max(axis=-1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="satu komentar sebagai string")
    ap.add_argument("--file", help="file csv/jsonl dengan kolom teks")
    ap.add_argument("--col", default="text", help="nama kolom teks (default: text)")
    ap.add_argument("--out", help="path output CSV (default: stdout)")
    ap.add_argument("--run", default="run1")
    args = ap.parse_args()

    if args.text:
        rows = [{"text": args.text}]
    elif args.file:
        fp = Path(args.file)
        if fp.suffix.lower() == ".jsonl":
            rows = [json.loads(l) for l in fp.read_text(encoding="utf-8") if l.strip()]
        else:
            rows = pd.read_csv(fp, encoding="utf-8-sig").to_dict("records")
        for r in rows:
            r["text"] = r.get(args.col, "")
    else:
        ap.error("berikan --text atau --file")

    model, tokenizer, device = load_model(args.run)
    labels, confs = predict([r["text"] for r in rows], model, tokenizer, device)

    out_rows = []
    for r, lab, conf in zip(rows, labels, confs):
        out_rows.append({"text": r["text"], "intent": lab, "confidence": round(float(conf), 4)})

    df = pd.DataFrame(out_rows)
    if args.out:
        df.to_csv(args.out, index=False, encoding="utf-8-sig")
        print("disimpan:", args.out)
    else:
        df.to_csv(sys.stdout, index=False)


if __name__ == "__main__":
    main()