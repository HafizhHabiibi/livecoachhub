"""
LiveCoachHub — Download Model dari Hugging Face Hub

Script ini mendownload model AI yang dibutuhkan dari Hugging Face Hub
ke lokasi yang tepat di project. Jalankan SEKALI setelah clone repo.

Usage:
    python scripts/download_models.py          # download semua model
    python scripts/download_models.py --nlp    # download NLP saja
    python scripts/download_models.py --llm    # download LLM adapter saja
"""

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Konfigurasi — sesuaikan repo_id setelah upload ke Hugging Face
# ---------------------------------------------------------------------------

# Ganti dengan username/repo HuggingFace kamu
NLP_REPO_ID = "HafizhHabiibi/livecoach-indobert-intent"
LLM_REPO_ID = "HafizhHabiibi/livecoach-qlora-adapter"

# Lokasi target di project
PROJECT_ROOT = Path(__file__).resolve().parent.parent
NLP_MODEL_DIR = PROJECT_ROOT / "AI" / "NLP" / "fine-tuned-indobert" / "outputs" / "models" / "indobert-intent" / "run1" / "best"
LLM_ADAPTER_DIR = PROJECT_ROOT / "AI" / "LLM" / "livecoach-qlora-adapter"


def download_nlp():
    """Download model NLP (IndoBERT fine-tuned) dari Hugging Face."""
    from huggingface_hub import snapshot_download

    print(f"\n📥 Downloading NLP model: {NLP_REPO_ID}")
    print(f"   Target: {NLP_MODEL_DIR}\n")

    NLP_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=NLP_REPO_ID,
        local_dir=str(NLP_MODEL_DIR),
        local_dir_use_symlinks=False,
    )

    # Verifikasi — GAGAL keras jika download tidak lengkap (C-10)
    config_file = NLP_MODEL_DIR / "config.json"
    if not config_file.exists():
        raise FileNotFoundError(
            f"❌ GAGAL: config.json tidak ditemukan di {NLP_MODEL_DIR}.\n"
            f"   Model belum terdownload dengan benar dari {NLP_REPO_ID}."
        )
    # Cek model weights (bisa .safetensors atau .bin)
    has_weights = (
        (NLP_MODEL_DIR / "model.safetensors").exists()
        or (NLP_MODEL_DIR / "pytorch_model.bin").exists()
    )
    if not has_weights:
        raise FileNotFoundError(
            f"❌ GAGAL: Model weights tidak ditemukan di {NLP_MODEL_DIR}.\n"
            f"   Download mungkin incomplete."
        )
    size_mb = sum(f.stat().st_size for f in NLP_MODEL_DIR.iterdir() if f.is_file()) / (1024 * 1024)
    print(f"✅ NLP model downloaded dan terverifikasi ({size_mb:.0f} MB)")


def download_llm():
    """Download adapter QLoRA (LLM) dari Hugging Face."""
    from huggingface_hub import snapshot_download

    print(f"\n📥 Downloading LLM adapter: {LLM_REPO_ID}")
    print(f"   Target: {LLM_ADAPTER_DIR}\n")

    LLM_ADAPTER_DIR.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=LLM_REPO_ID,
        local_dir=str(LLM_ADAPTER_DIR),
        local_dir_use_symlinks=False,
    )

    # Verifikasi — GAGAL keras jika download tidak lengkap (C-10)
    adapter_file = LLM_ADAPTER_DIR / "adapter_model.safetensors"
    config_file = LLM_ADAPTER_DIR / "adapter_config.json"
    if not config_file.exists():
        raise FileNotFoundError(
            f"❌ GAGAL: adapter_config.json tidak ditemukan di {LLM_ADAPTER_DIR}.\n"
            f"   Adapter belum terdownload dengan benar dari {LLM_REPO_ID}."
        )
    if not adapter_file.exists():
        raise FileNotFoundError(
            f"❌ GAGAL: adapter_model.safetensors tidak ditemukan di {LLM_ADAPTER_DIR}.\n"
            f"   Download mungkin incomplete."
        )
    size_mb = adapter_file.stat().st_size / (1024 * 1024)
    print(f"✅ LLM adapter downloaded dan terverifikasi ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description="Download model LiveCoachHub dari Hugging Face Hub")
    parser.add_argument("--nlp", action="store_true", help="Download NLP model saja")
    parser.add_argument("--llm", action="store_true", help="Download LLM adapter saja")
    args = parser.parse_args()

    # Cek dependency
    try:
        import huggingface_hub  # noqa: F401
    except ImportError:
        print("❌ huggingface_hub belum terinstall.")
        print("   Jalankan: pip install huggingface_hub")
        sys.exit(1)

    # Jika tidak ada flag spesifik, download semua
    download_all = not args.nlp and not args.llm

    if args.nlp or download_all:
        try:
            download_nlp()
        except Exception as e:
            print(f"❌ Gagal download NLP: {e}")

    if args.llm or download_all:
        try:
            download_llm()
        except Exception as e:
            print(f"❌ Gagal download LLM: {e}")

    print("\n🎉 Selesai! Model siap digunakan.")
    print("   Jalankan backend: cd backend && uvicorn app.main:app --port 8000")
    print("   Jalankan NLP:     cd AI/NLP && python fine-tuned-indobert/serve.py --port 8010")


if __name__ == "__main__":
    main()
