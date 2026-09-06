#!/usr/bin/env python3
"""Run the ordinary-transfer host compatibility and refusal fixtures."""
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent.parent


def main():
    with tempfile.TemporaryDirectory(prefix="ordinary-transfer-test-") as raw:
        directory = Path(raw)
        for name, flags in (("normal", ["-O0"]), ("optimized", ["-O2", "-DNDEBUG"])):
            output = directory / name
            subprocess.run([
                "cc", "-std=c11", "-Wall", "-Wextra", "-Werror", *flags,
                "-DORDINARY_TRANSFER_HOST_TEST", "-Isrc",
                "src/ordinary-transfer.c", "src/ordinary-transfer-test.c",
                "-o", str(output)], cwd=HERE, check=True)
            subprocess.run([str(output)], cwd=HERE, check=True)
    print("ordinary-transfer normal/optimized fixtures: pass")


if __name__ == "__main__":
    main()
