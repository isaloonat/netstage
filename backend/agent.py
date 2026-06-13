import json
from collections.abc import Generator

import anthropic

from .tools import audit_config, get_device_history, get_devices, plan_subnets

SYSTEM_PROMPT = (
    "You are NetSage, a network engineering assistant. Always use tools for facts "
    "about the network, subnet math, or config audits — never guess values you can "
    "compute or look up."
)

MODEL = "claude-sonnet-4-6"

TOOL_SCHEMAS = [
    {
        "name": "get_devices",
        "description": (
            "Get all network devices from NetPulse with their current status, "
            "latency, and uptime."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_device_history",
        "description": "Get the history of a specific device by IP address.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IP address of the device."}
            },
            "required": ["ip"],
        },
    },
    {
        "name": "plan_subnets",
        "description": (
            "Allocate VLSM subnets from a base CIDR given a list of named requirements. "
            "Uses largest-first allocation with power-of-2 block sizes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "base_cidr": {
                    "type": "string",
                    "description": "Base network in CIDR notation, e.g. '192.168.1.0/24'.",
                },
                "requirements": {
                    "type": "array",
                    "description": "Subnets to allocate.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "hosts": {"type": "integer", "description": "Number of usable hosts needed."},
                        },
                        "required": ["name", "hosts"],
                    },
                },
            },
            "required": ["base_cidr", "requirements"],
        },
    },
    {
        "name": "audit_config",
        "description": (
            "Audit a Cisco IOS configuration for security issues: telnet on VTY, "
            "missing service password-encryption, plaintext passwords, missing enable "
            "secret, ip http server, missing access-class on VTY."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "config_text": {
                    "type": "string",
                    "description": "Full Cisco IOS configuration text to audit.",
                }
            },
            "required": ["config_text"],
        },
    },
]


def _execute_tool(name: str, inputs: dict) -> dict:
    if name == "get_devices":
        return get_devices()
    if name == "get_device_history":
        return get_device_history(inputs["ip"])
    if name == "plan_subnets":
        return plan_subnets(inputs["base_cidr"], inputs["requirements"])
    if name == "audit_config":
        return audit_config(inputs["config_text"])
    return {"error": f"Unknown tool: {name}"}


def run_agent_stream(messages: list[dict], api_key: str) -> Generator[str, None, None]:
    """
    Runs the agent loop, yielding SSE-formatted event strings.

    Event shapes:
      {"type": "text", "delta": "..."}
      {"type": "tool_call_start", "name": "..."}
      {"type": "tool_result", "name": "...", "result": {...}}
      {"type": "done"}
      {"type": "error", "message": "..."}
    """
    client = anthropic.Anthropic(api_key=api_key)
    working_messages = list(messages)

    try:
        while True:
            with client.messages.stream(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=working_messages,
            ) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            yield f"data: {json.dumps({'type': 'tool_call_start', 'name': event.content_block.name})}\n\n"

                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield f"data: {json.dumps({'type': 'text', 'delta': event.delta.text})}\n\n"

                final_message = stream.get_final_message()

            if final_message.stop_reason == "end_turn":
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            if final_message.stop_reason == "tool_use":
                working_messages.append({"role": "assistant", "content": final_message.content})

                tool_results = []
                for block in final_message.content:
                    if block.type == "tool_use":
                        result = _execute_tool(block.name, block.input)
                        yield f"data: {json.dumps({'type': 'tool_result', 'name': block.name, 'result': result})}\n\n"
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })

                working_messages.append({"role": "user", "content": tool_results})
            else:
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
