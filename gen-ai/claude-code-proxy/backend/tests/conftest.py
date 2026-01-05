import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.append(str(root / "src"))
sys.path.append(str(root / "src" / "proxy"))
