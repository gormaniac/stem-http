"""The HTTP client code."""

import logging

import aiohttp
import aiohttp_socks

from . import tor


LOG = logging.getLogger(__name__)


class TorHttpClient:
    """An async HTTP client that uses a Tor Proxy."""

    def __init__(
        self,
        tor_proxy: tor.ProxyMgr,
        timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=90, connect=15),
        verify_ssl: bool = True,
    ) -> None:
        self.proxy = tor_proxy
        self.verify_ssl = verify_ssl
        self.connector = aiohttp_socks.ProxyConnector(host="127.0.0.1", port=self.proxy.socks_port)
        self.sess = aiohttp.ClientSession(connector=self.connector, timeout=timeout)

    async def close(self):
        """Close the client session."""

        await self.sess.close()

    async def request(self, method: str, url: str, **args):
        """Make an HTTP request - by adding it to the request queue."""

        try:
            result = await self.sess.request(
                method,
                url,
                verify_ssl=self.verify_ssl,
                **args
            )
        except Exception as err:
            LOG.error(
                "An error occurred during a %s request to %s: %s",
                *(method.upper(), url, str(err)),
                exc_info=True,
            )
            raise err

        return result

    async def get(self, url, **args):
        """Make an HTTP GET request."""

        return await self.request("get", url, **args)

    async def post(self, url, **args):
        """Make an HTTP POST request."""

        return await self.request("post", url, **args)

    async def put(self, url, **args):
        """Make an HTTP PUT request."""

        return await self.request("put", url, **args)
