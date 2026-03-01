"""Example: AITX Swarm Mesh provider node.

Demonstrates how to expose @aitx.tool()-decorated functions to the
zero-config mesh network. Any consumer on the same LAN can instantly
discover and execute these tools.
"""

import logging

import aitx
from aitx.mesh import serve_mesh

logging.basicConfig(level=logging.INFO)


@aitx.tool()
def get_system_metrics() -> dict:
    """Get current system CPU and memory usage.

    Returns:
        Dict with cpu_percent and memory_percent.
    """
    import psutil

    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
    }


@aitx.tool()
def analyze_text(text: str) -> dict:
    """Analyze the length and word count of text.

    Args:
        text: The text to analyze.
    """
    words = text.split()
    return {
        "length": len(text),
        "word_count": len(words),
        "preview": " ".join(words[:3]) + "..." if len(words) > 3 else text,
    }


if __name__ == "__main__":
    tools = [get_system_metrics, analyze_text]
    print("🚀 Starting AITX Mesh Provider 'metrics_node'...")
    print("   Tools:", [t.__name__ for t in tools])
    print("   Waiting for consumers...\n")
    serve_mesh(name="metrics_node", tools=tools, port=8888)
