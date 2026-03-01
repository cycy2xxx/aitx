"""Example of an AITX Swarm Mesh provider node.

This script demonstrates how to expose local Python functions as tools 
to the AITX zero-config mesh network. Any AITX consumer on the same 
network can instantly discover and use these tools without knowing the IP/Port.
"""
import logging
from aitx.mesh import serve_mesh

logging.basicConfig(level=logging.INFO)

# 1. Define your tools (normally these would also have @aitx.tool())
def get_system_metrics() -> dict:
    """Get current system CPU and memory usage as a demonstration."""
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
    }

def analyze_text(text: str) -> dict:
    """Analyze the length and word count of a piece of text."""
    words = text.split()
    return {
        "length": len(text),
        "word_count": len(words),
        "preview": " ".join(words[:3]) + "..." if len(words) > 3 else text,
    }

if __name__ == "__main__":
    tools = [get_system_metrics, analyze_text]
    print("🚀 Starting AITX Swarm Mesh Provider 'metrics_node'...")
    print("Serving tools:", [t.__name__ for t in tools])
    print("Waiting for consumers to discover us...\n")
    
    # 2. Serve them over the mesh. The name must be unique.
    serve_mesh(name="metrics_node", tools=tools, port=8888)
