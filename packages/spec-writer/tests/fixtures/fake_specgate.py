import sys
import yaml

value = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
asks = []

def walk(v):
    if isinstance(v, dict):
        for x in v.values():
            walk(x)
    elif isinstance(v, list):
        for x in v:
            walk(x)
    elif isinstance(v, str) and v.startswith("[ASK]"):
        asks.append(v)

walk(value)
raise SystemExit(3 if asks else 0)
