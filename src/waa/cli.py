# --- src/waa/cli.py ---
import argparse
import sounddevice as sd
from .app import run

def list_devices():
    print(sd.query_devices())

def main():
    p = argparse.ArgumentParser(prog="waa", description="Whisper Answer Assistant CLI")
    p.add_argument("--list-devices", action="store_true", help="List input devices")
    p.add_argument("--device", type=int, default=None, help="Mic device index")
    p.add_argument("--whisper-model", type=str, default="base",
                   help="tiny|base|small|medium|large-v3 or local path")
    p.add_argument("--config", type=str, default="configs/settings.yaml", help="Settings YAML")
    p.add_argument("--keywords", type=str, default="configs/keywords.en.txt", help="Keyword list")
    args = p.parse_args()

    if args.list_devices:
        list_devices()
        return

    run(
        device=args.device,
        whisper_model=args.whisper_model,
        config_path=args.config,
        keywords_path=args.keywords,
    )

if __name__ == "__main__":
    main()