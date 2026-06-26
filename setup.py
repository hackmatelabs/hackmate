#!/usr/bin/env python3
import subprocess
import sys

DEPENDENCIES = [
    ("textual", "textual"),
]

def ask(prompt: str) -> bool:
    while True:
        ans = input(prompt).strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False

def main():
    print("\n=== HackMate Setup ===\n")
    print("The following dependencies are required to run HackMate:\n")
    for name, _ in DEPENDENCIES:
        print(f"  - {name}")
    print()

    if not ask("Would you like to install them now? [y/n]: "):
        print()
        if not ask("Are you sure? HackMate will NOT work without these dependencies. Skip anyway? [y/n]: "):
            pass  # fall through to install
        else:
            print("\nSkipping install. Run setup.py again when you're ready.")
            sys.exit(0)

    print()
    failed = []
    for name, pkg in DEPENDENCIES:
        print(f"Installing {name}...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ERROR: failed to install {name}")
            print(result.stderr.strip())
            failed.append(name)
        else:
            print(f"  OK")

    print()
    if failed:
        print(f"Failed to install: {', '.join(failed)}")
        print("Try running: pip install " + " ".join(p for _, p in DEPENDENCIES))
        sys.exit(1)
    else:
        print("All dependencies installed. You can now run:")
        print("  Linux/macOS:  sudo python3 src/hackmate.py")
        print("  Windows:      python src\\hackmate.py  (as Administrator)")

if __name__ == "__main__":
    main()
