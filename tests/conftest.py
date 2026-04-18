import sys
from pathlib import Path

# Make project root importable so `import data, flow, prompts, db` works
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
