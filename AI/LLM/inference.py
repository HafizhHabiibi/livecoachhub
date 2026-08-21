"""
Inference Script untuk LiveCoach QLoRA LLM Model
Memuat Base Model Qwen2.5-1.5B-Instruct dalam format 4-bit NF4 (Kuantisasi Hemat VRAM ~1GB)
dan menggabungkannya dengan Adapter LoRA (livecoach-qlora-adapter).
Sesuai rekomendasi arsitektur: Qwen2.5-1.5B + 4-bit NF4 + QLoRA Adapter (8.7 MB).
"""

import json
import os
import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Import system_prompt dari grounded_llm
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "grounded_llm", "LLM dengan QLoRA"))
from system_prompt import SYSTEM_PROMPT

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
ADAPTER_DIR = Path("livecoach-qlora-adapter")


class LiveCoachInference:
    def __init__(self, base_model_name: str = BASE_MODEL, adapter_dir: Path = ADAPTER_DIR):
        print(f"[1/3] Memuat Tokenizer dari {base_model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        print(f"[2/3] Memuat Base Model {base_model_name} dalam 4-bit NF4 (Kuantisasi ~1GB RAM)...")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=bnb_config,
            device_map="auto",
        )

        print(f"[3/3] Memasang QLoRA Adapter dari {adapter_dir}...")
        self.model = PeftModel.from_pretrained(base_model, str(adapter_dir))
        self.model.eval()
        print("✓ Model LiveCoach 4-bit QLoRA siap digunakan untuk Inference!\n")

    def generate_response(self, user_payload: dict, max_new_tokens: int = 256, temperature: float = 0.7) -> dict:
        """
        Menerima user_payload (dict) dan mengembalikan respon teks dari model AI.
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]

        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True if temperature > 0 else False,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        generated_tokens = outputs[0][inputs["input_ids"].shape[1] :]
        raw_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()

        try:
            parsed_json = json.loads(raw_text)
            return {"status": "success", "raw_output": raw_text, "parsed": parsed_json}
        except json.JSONDecodeError:
            return {"status": "raw_text", "raw_output": raw_text}


def main():
    # Uji Coba Inferensi Lokal
    engine = LiveCoachInference()

    test_case = {
        "selected_action": "SHOW_SIZE_GUIDE",
        "audience_state": "SIZE_FRICTION",
        "evidence_comments": ["bb 70 cocok size apa ya kak", "aku agak gendutan nih"],
        "product_facts": [
            {
                "fact_id": "FACT-TS01-SIZE-XL",
                "value": "Size XL (dewasa): lingkar dada 112-116 cm, panjang baju 75 cm, cocok untuk BB 72-85 kg, TB 168-178 cm.",
            }
        ],
        "tone": "santai",
        "max_words": 30,
    }

    print("=== Menguji Kasus Inferensi ===")
    print("Input Payload:", json.dumps(test_case, indent=2, ensure_ascii=False))
    result = engine.generate_response(test_case)
    print("\nHasil Respon AI Model:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
