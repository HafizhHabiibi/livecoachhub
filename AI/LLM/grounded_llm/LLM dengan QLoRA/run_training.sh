#!/bin/bash
# Script untuk menjalankan proses training LLM dengan aman

# Pindah ke direktori tempat script ini berada (folder LLM)
cd "$(dirname "$0")"

echo "=== Persiapan Environment ==="

# Deteksi jika .venv memakai Python 3.14 yang bermasalah dan hapus jika ada Python 3.12
if [ -d ".venv" ]; then
    VENV_PY_VER=$(.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if [ "$VENV_PY_VER" == "3.14" ] && command -v python3.12 &> /dev/null; then
        echo "Mendeteksi Python 3.14 pada .venv. Menghapus dan membuat ulang menggunakan Python 3.12..."
        rm -rf .venv
    fi
fi

# Cek apakah virtual environment sudah ada
if [ ! -d ".venv" ]; then
    echo "Membuat virtual environment baru (.venv)..."
    
    # Gunakan Python 3.12 jika tersedia (sangat disarankan agar tidak perlu compile dari source)
    if command -v python3.12 &> /dev/null; then
        echo "Python 3.12 ditemukan! Membuat environment dengan Python 3.12..."
        python3.12 -m venv .venv
    else
        echo "Python 3.12 tidak ditemukan. Menggunakan Python default..."
        python3 -m venv .venv
    fi
fi

# Aktifkan virtual environment
echo "Mengaktifkan virtual environment..."
source .venv/bin/activate

# --- PERBAIKAN BUG INSTALASI DI PYTHON 3.14 & GCC 14 ---
# Python 3.14 masih sangat baru, library PyO3 membutuhkan flag kompabilitas agar bisa compile.
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
# GCC 14 menganggap fungsi tanpa parameter `()` sebagai `(void)`. Hal ini membuat C code lama menjadi error.
# Kita kembalikan standar ke C17 agar onig_sys dan tokenizers berhasil di-compile.
export CFLAGS="-std=gnu17 -Wno-error=incompatible-pointer-types"
export CXXFLAGS="-std=gnu17 -Wno-error=incompatible-pointer-types"

# Install requirements
echo "Menginstall dependencies (library) yang dibutuhkan..."
pip install -r "grounded_llm/LLM dengan QLoRA/requirements_qlora.txt"

echo "=== Memulai Training ==="
# Mencegah memory fragmentation pada GPU yang VRAM-nya pas-pasan
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
# Jalankan script training
python train_llm.py
