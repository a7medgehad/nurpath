#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from app.api.deps import get_pipeline


def main() -> None:
    mermaid = get_pipeline().mermaid()
    output = Path(__file__).resolve().parents[1] / "docs" / "langgraph_agent_flow.mmd"
    output.write_text(mermaid + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
