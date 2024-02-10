"""The HTTP client code."""

import logging
from typing import Any, Mapping, Optional

import aiohttp
import aiohttp.typedefs
import aiohttp_socks

from . import tor


LOG = logging.getLogger(__name__)


class TorHttpClient:
    """An async HTTP client that uses a Tor Proxy.

    The Tor proxy should be managed by the ``tor.ProxyMgr`` class.

    Parameters
    ----------
    tor_proxy : tor.ProxyMgr
        An object that manages a local Tor proxy.
    timeout : aiohttp.ClientTimeout, optional
        A custom timeout object for requests,
        by default ``aiohttp.ClientTimeout(total=90, connect=15)``.
    verify_ssl : bool, optional
        Whether to verify SSL certificates during requests, by default True.
    """

    def __init__(
        self,
        tor_proxy: tor.ProxyMgr,
        timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=90, connect=15),
        verify_ssl: bool = True,
    ) -> None:
        self.proxy = tor_proxy
        self.verify_ssl = verify_ssl
        self.connector = aiohttp_socks.ProxyConnector(
            host="127.0.0.1", port=self.proxy.socks_port
        )
        self.sess = aiohttp.ClientSession(connector=self.connector, timeout=timeout)

    async def close(self):
        """Close the client session."""

        await self.sess.close()

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Mapping[str, str]] = None,
        data: Any = None,
        json: dict | None = None,
        cookies: Optional[aiohttp.typedefs.LooseCookies] = None,
        headers: Optional[aiohttp.typedefs.LooseHeaders] = None,
        auth: Optional[aiohttp.BasicAuth] = None,
        **kwargs,
    ):
        """Make an HTTP request - by adding it to the request queue.

        Parameters
        ----------
        method : str
            The HTTP method of the request.
        url : str
            The URL to make a request to.
        params : Optional[Mapping[str, str]], optional
            Optional URL params to add to the URL, by default ``None``.
        data : Any, optional
            Arbitrary data to send in the body of the request, by default ``None``.
        json : dict | None, optional
            An optional JSON payload to include in the body, by default ``None``.
        cookies : Optional[aiohttp.typedefs.LooseCookies], optional
            Optional cookies to send with the request, by default ``None``.
        headers : Optional[aiohttp.typedefs.LooseHeaders], optional
            Optional headers to send with the request, by default ``None``.
        auth : Optional[aiohttp.BasicAuth], optional
            Optionally authenticate the request with this object, by default ``None``.

        Returns
        -------
        aiohttp.ClientResponse
            The response of the request.

        Raises
        ------
        err
            Any Exception raised when making the request.
            The non-exhaustive list::

                RuntimeError
                TypeError
                ValueError
                aiohttp.ClientError
                asyncio.TimeoutError

        """

        try:
            result = await self.sess.request(
                method,
                url,
                params=params,
                data=data,
                json=json,
                cookies=cookies,
                headers=headers,
                auth=auth,
                verify_ssl=self.verify_ssl,
                **kwargs,
            )
        except Exception as err:
            LOG.error(
                "An error occurred during a %s request to %s: %s",
                *(method.upper(), url, str(err)),
                exc_info=True,
            )
            raise err

        return result

    async def get(
        self,
        url,
        params: Optional[Mapping[str, str]] = None,
        cookies: Optional[aiohttp.typedefs.LooseCookies] = None,
        headers: Optional[aiohttp.typedefs.LooseHeaders] = None,
        auth: Optional[aiohttp.BasicAuth] = None,
        **kwargs,
    ):
        """Make an HTTP GET request."""

        return await self.request(
            "get",
            url,
            params=params,
            cookies=cookies,
            headers=headers,
            auth=auth**kwargs,
        )

    async def post(
        self,
        url: str,
        params: Optional[Mapping[str, str]] = None,
        data: Any = None,
        json: dict | None = None,
        cookies: Optional[aiohttp.typedefs.LooseCookies] = None,
        headers: Optional[aiohttp.typedefs.LooseHeaders] = None,
        auth: Optional[aiohttp.BasicAuth] = None,
        **kwargs,
    ):
        """Make an HTTP POST request."""

        return await self.request(
            "post",
            url,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            headers=headers,
            auth=auth,
            **kwargs,
        )

    async def put(
        self,
        url: str,
        params: Optional[Mapping[str, str]] = None,
        data: Any = None,
        json: dict | None = None,
        cookies: Optional[aiohttp.typedefs.LooseCookies] = None,
        headers: Optional[aiohttp.typedefs.LooseHeaders] = None,
        auth: Optional[aiohttp.BasicAuth] = None,
        **kwargs,
    ):
        """Make an HTTP PUT request."""

        return await self.request(
            "put",
            url,
            params=params,
            data=data,
            json=json,
            cookies=cookies,
            headers=headers,
            auth=auth,
            **kwargs,
        )
