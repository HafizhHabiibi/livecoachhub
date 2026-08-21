import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parent

app = FastAPI(title="NLP Intent Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_run = "run1"
_model = None
_tokenizer = None
_intents = None
_id2label = None


class PredictRequest(BaseModel):
    texts: list[str]
    threshold: float | None = None


class LoadRequest(BaseModel):
    run: str = "run1"


def _load(run):
    global _run, _model, _tokenizer, _intents, _id2label
    _run = run
    model_dir = ROOT / "outputs" / "models" / "indobert-intent" / run / "best"
    if not model_dir.exists():
        raise FileNotFoundError(f"checkpoint tidak ditemukan: {model_dir}")
    with open(ROOT.parent / "data" / "processed" / "indobert_dataset" / "dataset_info.json", "r", encoding="utf-8") as f:
        info = json.load(f)
    _intents = info["intent_map"]
    _id2label = {v: k for k, v in _intents.items()}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    _model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).to(device)
    _model.eval()


def _ensure():
    if _model is None:
        _load(_run)


@app.get("/health")
def health():
    _ensure()
    return {"status": "ok", "model": _run, "device": str(next(_model.parameters()).device)}


@app.get("/intents")
def intents():
    _ensure()
    return {"intents": _intents}


@app.post("/predict")
def predict(req: PredictRequest):
    _ensure()
    texts = [str(t) for t in req.texts]
    device = next(_model.parameters()).device
    all_logits = []
    for i in range(0, len(texts), 32):
        enc = _tokenizer(
            texts[i:i + 32], padding=True, truncation=True, max_length=64, return_tensors="pt"
        ).to(device)
        with torch.no_grad():
            all_logits.append(_model(**enc).logits.cpu().numpy())
    probs = torch.softmax(torch.from_numpy(np.concatenate(all_logits)), dim=-1).numpy()
    results = []
    for text, row in zip(texts, probs):
        idx = int(row.argmax())
        conf = float(row[idx])
        intent = _id2label[idx]
        if req.threshold is not None and conf < req.threshold:
            intent = "other"
        results.append({"text": text, "intent": intent, "confidence": round(conf, 4)})
    return {"results": results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="run1")
    ap.add_argument("--port", type=int, default=8010)
    args = ap.parse_args()
    _load(args.run)
    print(f"model '{args.run}' dimuat. jalankan server di :{args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()