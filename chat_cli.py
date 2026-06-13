#!/usr/bin/env python3
"""Terminal REPL for testing NetSage without the frontend."""
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from backend.agent import run_agent_stream


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    print("NetSage CLI — Ctrl+C to exit\n")
    messages: list[dict] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        print("NetSage: ", end="", flush=True)

        assistant_text = []

        for raw in run_agent_stream(list(messages), api_key):
            if not raw.startswith("data: "):
                continue
            event = json.loads(raw[6:])

            if event["type"] == "text":
                print(event["delta"], end="", flush=True)
                assistant_text.append(event["delta"])
            elif event["type"] == "tool_call_start":
                print(f"\n  [→ {event['name']}]", end="", flush=True)
            elif event["type"] == "tool_result":
                snippet = json.dumps(event["result"])[:120]
                print(f"\n  [← {event['name']}: {snippet}]", end="", flush=True)
            elif event["type"] == "error":
                print(f"\nError: {event['message']}", file=sys.stderr)
            elif event["type"] == "done":
                print()

        messages.append({"role": "assistant", "content": "".join(assistant_text)})


if __name__ == "__main__":
    main()
