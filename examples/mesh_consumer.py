"""Example of an AITX Swarm Mesh consumer.

This script demonstrates discovering available AITX tools on the local 
network and executing them dynamically.
"""
import asyncio
from aitx.mesh import discover_tools, MeshClient

async def main():
    print("🔍 Discovering AITX tools on the local network (waiting 3 seconds)...")
    
    # 1. Discover available nodes
    nodes = await discover_tools(timeout=3.0)
    
    if not nodes:
        print("❌ No AITX mesh nodes found. Make sure mesh_provider.py is running in another terminal.")
        return

    print(f"\n✅ Found {len(nodes)} node(s):")
    for node in nodes:
        print(f"  - Node: {node['node']} at {node['host']}:{node['port']}")
        print(f"    Available Tools: {', '.join(node['tools'])}")

    # 2. Pick the first node and execute a tool
    target = nodes[0]
    print(f"\n⚡ Connecting to '{target['node']}' to execute tools...")
    
    async with MeshClient(target["host"], target["port"]) as client:
        # Example 1: Call analyze_text
        if "analyze_text" in target["tools"]:
            print("\n→ Executing 'analyze_text'...")
            result = await client.execute("analyze_text", {"text": "AITX Swarm is revolutionary for AI interoperability."})
            print(f"← Result: {result}")
            
        # Example 2: Call get_system_metrics
        if "get_system_metrics" in target["tools"]:
            print("\n→ Executing 'get_system_metrics'...")
            result = await client.execute("get_system_metrics")
            print(f"← Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
