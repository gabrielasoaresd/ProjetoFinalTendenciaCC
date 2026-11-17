from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from compgraph.pipeline import run_ingestion

if __name__ == "__main__":
    summary = run_ingestion()
    print("Ingestão concluída:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
