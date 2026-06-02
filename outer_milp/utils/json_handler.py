import json
import sys


def load_problem(filepath: str) -> dict:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[json_handler] Loaded: {filepath}", file=sys.stderr)
        return data
    except FileNotFoundError:
        raise FileNotFoundError(
            f"json_handler.load_problem: file not found: {filepath}"
        )
    except json.JSONDecodeError as exc:
        raise json.JSONDecodeError(
            f"json_handler.load_problem: invalid JSON in {filepath}: {exc.msg}",
            exc.doc,
            exc.pos,
        )


def save_problem(data: dict, filepath: str) -> None:
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[json_handler] Saved: {filepath}", file=sys.stderr)
    except OSError as exc:
        raise IOError(
            f"json_handler.save_problem: cannot write to {filepath}: {exc}"
        ) from exc
