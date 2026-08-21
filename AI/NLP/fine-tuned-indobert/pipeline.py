import argparse
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

console = Console()


def run_script(rel_path: str, args=None):
    script = ROOT / rel_path
    if not script.exists():
        raise FileNotFoundError(f"script tidak ditemukan: {script}")
    cmd = [PY, "-X", "utf8", str(script)] + (args or [])
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=str(ROOT))
    if proc.returncode != 0:
        console.print(
            f"[bold red]GAGAL di {rel_path} (exit {proc.returncode})[/bold red]"
        )
        raise SystemExit(proc.returncode)
    return time.monotonic() - t0


def has(path: str) -> bool:
    return (ROOT / path).exists()


def run_step(name: str, scripts: list, force: bool, skip_if_exist: list | None = None,
             extra_args: list | None = None):
    if skip_if_exist and not force and all(has(p) for p in skip_if_exist):
        console.print(f"[yellow]skip[/yellow] {name} — aset sudah ada "
                      f"({', '.join(skip_if_exist)}) | pakai --force untuk jalankan ulang")
        return

    console.rule(f"[bold]{name}[/bold]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=24),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task(f"0/{len(scripts)} langkah", total=len(scripts))
        for rel in scripts:
            progress.update(task, description=f"[cyan]{rel}[/cyan]")
            dt = run_script(rel, extra_args)
            progress.advance(task)
            console.print(f"  [green]ok[/green] {rel} ({dt:.1f}s)")
        progress.update(task, description="selesai", completed=len(scripts))
    console.print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="run1", help="nama run training (default: run1)")
    ap.add_argument("--data-only", action="store_true",
                    help="hentikan setelah build dataset (tanpa train & evaluate)")
    ap.add_argument("--skip-train", action="store_true", help="lewati langkah training")
    ap.add_argument("--only", help="koma-terpisah dari langkah yang dijalankan saja: "
                                   "preprocess,dataset,split,train,evaluate")
    ap.add_argument("--force", action="store_true",
                    help="jalankan ulang langkah yang biasanya di-skip")
    args = ap.parse_args()

    pipeline = [
        ("preprocess", "1/6 preprocessing komentar",
         ["fine-tuned-indobert/preprocessing/extract_unique.py", "fine-tuned-indobert/preprocessing/merge_labels.py"],
         ["data/processed/comments_labeled.csv"]),
        ("relabel", "2/6 relabel komentar asli (rule engine)",
         ["fine-tuned-indobert/dataset/relabel.py"],
         ["data/dataset/relabel_draft.csv"]),
        ("dataset", "3/6 rakit dataset lengkap (augmentasi + dedupe + validasi)",
         ["fine-tuned-indobert/dataset/mark_sentiment.py", "fine-tuned-indobert/dataset/combine.py", "fine-tuned-indobert/dataset/dedupe.py",
           "fine-tuned-indobert/dataset/to_jsonl.py", "fine-tuned-indobert/dataset/validate.py"],
         ["data/dataset/tiktok_live_10k.jsonl"]),
        ("split", "4/6 split train/val/test",
         ["fine-tuned-indobert/preprocessing/build_dataset.py"],
         []),
        ("train", "5/6 fine-tuning IndoBERT",
         ["fine-tuned-indobert/train.py"],
         []),
        ("evaluate", "6/6 evaluasi + threshold",
         ["fine-tuned-indobert/evaluate.py", "fine-tuned-indobert/threshold.py"],
         []),
    ]

    only = None
    if args.only:
        only = {x.strip() for x in args.only.split(",")}
    keys = [k for k, *_ in pipeline]
    bad = only - set(keys) if only else set()
    if bad:
        console.print(f"[bold red]langkah tidak dikenal: {sorted(bad)}[/bold red] "
                      f"(pilihan: {', '.join(keys)})")
        raise SystemExit(1)
    if args.data_only:
        pipeline = pipeline[:4]
    elif args.skip_train:
        pipeline = [s for s in pipeline if s[0] not in ("train", "evaluate")]

    console.print(f"[bold]Pipeline dimulai[/bold] — run: [cyan]{args.run}[/cyan] | "
                  f"python: {PY}\n")

    for key, name, scripts, skip in pipeline:
        if only and key not in only:
            console.print(f"[dim]skip langkah (--only): {name}[/dim]")
            continue
        step_args = ["--run", args.run] if key in ("train", "evaluate") else []
        run_step(name, scripts, args.force, skip, step_args)

    console.rule("[bold green]Pipeline selesai[/bold green]")


if __name__ == "__main__":
    main()