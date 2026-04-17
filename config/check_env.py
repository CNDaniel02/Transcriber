from __future__ import annotations

import shutil
import subprocess
import sys


def print_header(name: str) -> None:
    print(f"\n=== {name} ===")


def check_python() -> bool:
    print_header("Python")
    print(f"Version: {sys.version}")
    return True


def check_ffmpeg() -> bool:
    print_header("FFmpeg")
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        print("FAIL: ffmpeg not found in PATH")
        return False

    print(f"Found: {ffmpeg_path}")
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        first_line = result.stdout.splitlines()[0] if result.stdout else "unknown"
        print(f"Version: {first_line}")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"FAIL: ffmpeg execution failed: {exc.stderr.strip()}")
        return False


def check_torch() -> bool:
    print_header("Torch + CUDA")
    try:
        import torch  # pylint: disable=import-error
    except ImportError as exc:
        print(f"FAIL: torch import failed: {exc}")
        return False

    print(f"Torch version: {torch.__version__}")
    cuda_ok = torch.cuda.is_available()
    print(f"CUDA available: {cuda_ok}")
    if cuda_ok:
        print(f"CUDA runtime: {torch.version.cuda}")
        print(f"GPU count: {torch.cuda.device_count()}")
        print(f"GPU[0]: {torch.cuda.get_device_name(0)}")
    else:
        print("WARN: CUDA unavailable. Pipeline will fall back to CPU.")
    return True


def check_whisper() -> bool:
    print_header("Whisper")
    try:
        import whisper  # pylint: disable=import-error
    except ImportError as exc:
        print(f"FAIL: whisper import failed: {exc}")
        return False

    print(f"Whisper module: {whisper.__file__}")
    return True


def main() -> int:
    checks = [check_python, check_ffmpeg, check_torch, check_whisper]
    results = [fn() for fn in checks]
    ok = all(results)
    print("\n=== Result ===")
    if ok:
        print("PASS: Environment looks ready.")
        return 0
    print("FAIL: One or more checks failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
