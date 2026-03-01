"""MeshAdvertiser: mDNS service advertisement for AITX mesh nodes."""
from __future__ import annotations

import asyncio
import logging
import socket

from zeroconf import ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)


class MeshAdvertiser:
    """Broadcasts the presence of an AITX mesh node on the local network.

    Uses zeroconf to register a ``_aitx._tcp.local.`` mDNS service so that
    :class:`~aitx.mesh.router.MeshRouter` instances can discover it.
    """

    SERVICE_TYPE = "_aitx._tcp.local."

    def __init__(self, name: str, port: int) -> None:
        self.name = name
        self.port = port
        self.is_running = False
        self._zeroconf: Zeroconf | None = None
        self._info: ServiceInfo | None = None

    async def start(self) -> None:
        """Register the mDNS service and begin advertising."""
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

        loop = asyncio.get_running_loop()
        self._zeroconf = await loop.run_in_executor(None, Zeroconf)
        await loop.run_in_executor(
            None, self._zeroconf.register_service, self._info
        )

        self.is_running = True
        logger.info(
            "Advertising AITX mesh node '%s' on %s:%d",
            self.name, local_ip, self.port,
        )

    async def stop(self) -> None:
        """Unregister the mDNS service and stop advertising."""
        if not self.is_running or not self._zeroconf or not self._info:
            return

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, self._zeroconf.unregister_service, self._info
        )
        await loop.run_in_executor(None, self._zeroconf.close)

        self._zeroconf = None
        self._info = None
        self.is_running = False
        logger.info("Stopped advertising AITX mesh node '%s'", self.name)
