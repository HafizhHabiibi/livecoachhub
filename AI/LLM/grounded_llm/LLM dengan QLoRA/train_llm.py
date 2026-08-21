import json
import sys
import os
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTTrainer

# Import system_prompt dari folder grounded_llm
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "grounded_llm", "LLM dengan QLoRA"))
from system_prompt import SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
DATASET_PATH = Path("grounded_llm/Response Dataset/response_dataset.jsonl")
OUTPUT_DIR = "livecoach-qlora-adapter"
MAX_SEQ_LENGTH = 1024

LORA_CONFIG = LoraConfig(
    r=8,                # rank kecil -- dataset cuma 60 contoh, hindari overfit
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # attention layers Qwen2
)

TRAINING_ARGS = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=4,             # epoch sedikit -- data kecil, rawan overfit/hafalan
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,  # efektif batch size 8
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=5,
    save_strategy="epoch",
    bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
    report_to="none",
    gradient_checkpointing=True,    # Mencegah OOM (Out Of Memory) di GPU 8GB (RTX 4060)
    gradient_checkpointing_kwargs={"use_reentrant": False},
)


# ---------------------------------------------------------------------------
# 1. Load dan format dataset jadi chat template
# ---------------------------------------------------------------------------

def load_dataset(path: Path) -> Dataset:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            user_payload = {
                "selected_action": entry["input"]["selected_action"],
                "audience_state": entry["input"]["audience_state"],
                "evidence_comments": entry["input"]["evidence_comments"],
                "product_facts": entry["input"]["product_facts"],
                "tone": entry["input"]["tone"],
                "max_words": entry["input"]["max_words"],
            }
            assistant_payload = entry["output"]

            rows.append(
                {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                        {"role": "assistant", "content": json.dumps(assistant_payload, ensure_ascii=False)},
                    ]
                }
            )
    return Dataset.from_list(rows)


def formatting_func(example, tokenizer):
    return tokenizer.apply_chat_template(
        example["messages"], tokenize=False, add_generation_prompt=False
    )


# ---------------------------------------------------------------------------
# 2. Load base model 4-bit + siapkan LoRA
# ---------------------------------------------------------------------------

def build_model_and_tokenizer():
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LORA_CONFIG)
    model.print_trainable_parameters()

    return model, tokenizer


# ---------------------------------------------------------------------------
# 3. Main
# ---------------------------------------------------------------------------

def main():
    dataset = load_dataset(DATASET_PATH)
    print(f"Loaded {len(dataset)} training examples.")

    model, tokenizer = build_model_and_tokenizer()

    # Menerapkan chat template secara eksplisit agar lebih stabil dibanding formatting_func runtime
    dataset = dataset.map(
        lambda ex: {"text": tokenizer.apply_chat_template(ex["messages"], tokenize=False, add_generation_prompt=False)}
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=TRAINING_ARGS,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        tokenizer=tokenizer,
    )

    trainer.train()

    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"Adapter tersimpan di: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
