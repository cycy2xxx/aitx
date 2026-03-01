"""Example AITX Swarm Mesh consumer using MeshRouter.

This script demonstrates automatic tool routing: you don't need to know
which node hosts which tool — the router handles it transparently.
"""

import asyncio
import logging
from aitx.mesh import MeshRouter

logging.basicConfig(level=logging.INFO)


async def main():
    router = MeshRouter()
    await router.start()

    print("🔍 Discovering AITX tools on the local network (waiting 3 seconds)...")
    await asyncio.sleep(3)

    tools = router.available_tools
    if not tools:
        print("❌ No tools found. Make sure mesh_provider.py is running.")
        await router.stop()
        return

    print(f"\n✅ Discovered {len(tools)} tool(s): {', '.join(tools)}")

    # ── Execute tools transparently — no manual node selection ──
    if "analyze_text" in tools:
        print("\n→ router.execute('analyze_text', ...)")
        result = await router.execute(
            "analyze_text", {"text": "AITX Swarm Router is revolutionary!"}
        )
        print(f"← Result: {result}")

    if "get_system_metrics" in tools:
        print("\n→ router.execute('get_system_metrics')")
        result = await router.execute("get_system_metrics")
        print(f"← Result: {result}")

    # ── Inspect a remote tool's schema ──
    schema = router.get_tool_schema("analyze_text")
    if schema:
        print(f"\n📋 Schema for 'analyze_text': {schema}")

    await router.stop()
    print("\n✨ Done!")


if __name__ == "__main__":
    asyncio.run(main())
