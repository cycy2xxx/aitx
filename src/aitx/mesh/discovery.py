import asyncio
import socket
from zeroconf import ServiceInfo, Zeroconf
import logging

logger = logging.getLogger(__name__)

class MeshAdvertiser:
    """Advertises an AITX mesh node over mDNS using zeroconf."""
    
    SERVICE_TYPE = "_aitx._tcp.local."

    def __init__(self, name: str, port: int):
        self.name = name
        self.port = port
        self.is_running = False
        self._zeroconf: Zeroconf | None = None
        self._info: ServiceInfo | None = None

    async def start(self) -> None:
        """Starts advertising the service."""
        if self.is_running:
            return

        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)

        self._info = ServiceInfo(
            self.SERVICE_TYPE,
            f"{self.name}.{self.SERVICE_TYPE}",
            addresses=[socket.inet_aton(local_ip)],
            port=self.port,
            properties={"version": "0.1.0"},
            server=f"{hostname}.local.",
        )

        # Run zeroconf blocking calls in an executor
        loop = asyncio.get_running_loop()
        self._zeroconf = await loop.run_in_executor(None, Zeroconf)
        await loop.run_in_executor(None, self._zeroconf.register_service, self._info)
        
        self.is_running = True
        logger.info(f"Advertising AITX mesh node '{self.name}' on {local_ip}:{self.port}")

    async def stop(self) -> None:
        """Stops advertising the service."""
        if not self.is_running or not self._zeroconf or not self._info:
            return

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._zeroconf.unregister_service, self._info)
        await loop.run_in_executor(None, self._zeroconf.close)
        
        self._zeroconf = None
        self._info = None
        self.is_running = False
        logger.info(f"Stopped advertising AITX mesh node '{self.name}'")
