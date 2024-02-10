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
    tor_proxy : tor.ProxyMgr | None, optional
        An object that manages a local Tor proxy, by default ``None``.
        If ``None``, a custom socks proxy addr/port can be passed. If all
        are ``None``, no proxy is used and this object becomes a simple
        aiohttp wrapper. Not using the ``tor_proxy`` arg means that countries
        cannot be managed by this object.
    proxy_addr : str | None, optional
        A custom socks proxy address to use, by default ``None``.
    proxy_port : int | None, optional
        The port that the custom socks proxy uses, by default ``None``.
    timeout : aiohttp.ClientTimeout, optional
        A custom timeout object for requests, by default
        ``aiohttp.ClientTimeout(total=90, connect=15)``.
    verify_ssl : bool, optional
        Whether to verify SSL certificates during requests, by default ``True``.

    Properties
    ----------
    tor_proxy : tor.ProxyMgr | None
        The object that manages the local Tor proxy.
    verify_ssl : bool
        Whether requests verify SSL certificates.
    managed_tor : bool
        True when ``tor_proxy`` is not ``None``. Gates whether managed Tor actions
        can be taken by this object, like changing countries.
    connector : aiohttp.BaseConnector
        The connector to use with requests. Can be either ``BaseConnector`` or
        an ``aiohttp_socks.ProxyConnector``.
    sess : aiohttp.ClientSession
        The session object used for all requests made by this object.
    """

    def __init__(
        self,
        tor_proxy: tor.ProxyMgr | None = None,
        proxy_addr: str | None = None,
        proxy_port: int | None = None,
        timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=90, connect=15),
        verify_ssl: bool = True,
    ) -> None:
        self.tor_proxy = tor_proxy
        self.verify_ssl = verify_ssl
        self.managed_tor = False

        if isinstance(self.tor_proxy, tor.ProxyMgr):
            self.connector = aiohttp_socks.ProxyConnector(
                host="127.0.0.1", port=self.tor_proxy.socks_port
            )
            self.managed_tor = True
        elif proxy_addr is not None and proxy_port is not None:
            self.connector = aiohttp_socks.ProxyConnector(
                host=proxy_addr, port=proxy_port
            )
        else:
            self.connector = aiohttp.BaseConnector()

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
