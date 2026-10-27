"""Génère les trois portefeuilles fictifs et leur vérité dans data/samples/."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alea.synth import generate_all  # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    m = generate_all(ROOT / "data" / "samples")
    print(json.dumps(m, ensure_ascii=False, indent=2))
    print(f"terminé en {time.time() - t0:.1f} s")
