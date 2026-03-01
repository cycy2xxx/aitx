"""Example: Using aitx with OpenAI (no API key required — shows schema only).

Demonstrates the core value proposition: decorate a function once,
get ready-to-use schemas for any platform.
"""

import json

import aitx


@aitx.tool()
def get_weather(city: str, units: str = "celsius") -> dict:
    """Get current weather for a city.

    Args:
        city: City name (e.g. "Tokyo")
        units: Temperature units
    """
    return {"city": city, "temp": 22, "units": units}


@aitx.tool()
def search(query: str, limit: int = 5) -> list[dict]:
    """Search documents by keyword.

    Args:
        query: Search query string.
        limit: Maximum number of results.
    """
    return [{"title": f"Result for '{query}'", "score": 0.95}]


tools = [get_weather, search]

print("=" * 60)
print("AITX Core Pipeline Demo")
print("=" * 60)

# ── Schema Generation ─────────────────────────────────────────
print("\n📋 OpenAI schemas:")
for schema in aitx.to_openai(tools):
    print(json.dumps(schema, indent=2))

print("\n📋 Anthropic schemas:")
for schema in aitx.to_anthropic(tools):
    print(json.dumps(schema, indent=2))

# ── Dispatch Simulation ──────────────────────────────────────
print("\n⚡ Simulating OpenAI tool call dispatch:")
fake_openai_response = {
    "choices": [
        {
            "message": {
                "tool_calls": [
                    {
                        "id": "call_abc123",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": json.dumps({"city": "Tokyo"}),
                        },
                    }
                ]
            }
        }
    ]
}
results = aitx.handle_openai(fake_openai_response, tools)
print(json.dumps(results, indent=2))

print("\n⚡ Simulating Anthropic tool call dispatch:")
fake_anthropic_response = {
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_abc123",
            "name": "search",
            "input": {"query": "AI tools", "limit": 3},
        }
    ]
}
results = aitx.handle_anthropic(fake_anthropic_response, tools)
print(json.dumps(results, indent=2))

print("\n✨ Same functions. Any platform. Zero boilerplate.")
