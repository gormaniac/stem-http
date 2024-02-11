"""Manage the Tor proxy."""

import subprocess
from typing import Optional

import stem
import stem.control
import stem.process


BIND_FAIL_MSG = "Process terminated: Failed to bind one of the listener ports."


class ProxyMgr:
    """Manages a Tor Proxy process attached to the calling process.

    May be used as a contextmanager that automatically kills the Tor
    process when it exits.

    TODO - Support country changes
    TODO - Expose a method to open raw sockets through the proxy.

    Parameters
    ----------
    reuse : bool, optional
        Reuse an existing Tor proxy, by default ``False``.
    retry : bool, optional
        Try starting a managed Tor process multiple times until one can start,
        by default ``True``.
    countries : Optional[list], optional
        A list of countries to use as exit nodes, by default ``None``.
    passw : Optional[str], optional
        An optional password to authenticate to the Tor proxy's control port,
        by default ``None``.
    socks_port : int, optional
        The port of the Tor SOCKS proxy to connect to or use in managed processes. Retries
        will change this port as needed until a valid port is found. By default ``9050``. 
    cntrl_port : int, optional
        The Tor proxy's control port to connect to, by default ``9051``.
    exit_on_reuse_fail : bool, optional
        Raise an exception if reusing an existing proxy fails. If ``False``, the object
        tries to start a managed process on the specified ports when reuse fails.
        By default ``False``.

    Raises
    ------
    RuntimeError
        When reusing a proxy fails and ``exit_on_reuse_fail`` is ``True``.
    """

    def __init__(
        self,
        reuse: bool = False,
        retry: bool = True,
        countries: Optional[list] = None,
        passw: Optional[str] = None,
        socks_port: int = 9050,
        cntrl_port: int = 9051,
        exit_on_reuse_fail: bool = False
    ) -> None:
        self.cntrl_passw = passw
        self.reuse = reuse
        self.retry = retry
        self.countries = countries

        self.socks_port = socks_port
        self.cntrl_port = cntrl_port

        self.process: subprocess.Popen | None = None
        self.cntrlr: stem.control.Controller | None = None

        if self.reuse:
            try:
                self.connect_cntrlr()
            except stem.SocketError as err:
                if exit_on_reuse_fail:
                    raise RuntimeError("No existing Tor proxy to connect to.") from err
                self.reuse = False

        # This is not an `else` because an error above can set self.reuse to False.
        if not self.reuse:
            self.start()
            self.connect_cntrlr()

    def connect_cntrlr(self):
        """Connect to the configured Tor proxy's Control port."""

        self.cntrlr = stem.control.Controller.from_port(port=self.cntrl_port)
        self.cntrlr.authenticate(password=self.cntrl_passw)

    def start(self, retries=10):
        """Start a managed Tor process.

        Supports retrying the process if an existing process owns the SOCKS or
        control ports. This allows multiple instances of this class to run.
        The number of instances is can be limited by the number of retries.

        Parameters
        ----------
        retries : int, optional
            The max number of times to try starting a new process, by default ``10``.
            Set this to ``0`` to disable the retry behavior.

        Raises
        ------
        RuntimeError
            When the max number of retries is reached and no process is started.
        OSError
            When there's an error starting the Tor subprocess.
        """

        try:
            self.process: subprocess.Popen = stem.process.launch_tor_with_config(
                config={
                    "ControlPort": str(self.cntrl_port),
                    "SocksPort": str(self.socks_port),
                },
                take_ownership=True,
            )
        except OSError as err:
            if str(err) == BIND_FAIL_MSG and self.retry and retries > 0:
                self.socks_port += 2
                self.cntrl_port += 2
                # TODO - Make retries configurable? This limits number of instances.
                retries -= 1
                self.start(retries=retries)
            elif retries == 0:
                raise RuntimeError("Max number of ProxyMgr instances reached!") from err
            else:
                raise err

    def stop(self):
        """Kill the tor process.

        Must be done before exiting Python or the tor process may persist.
        The process is supposed to be killed when Python is killed, but this
        allows for it to happen gracefully, and with the caller's control.

        Has no effect when reusing an existing Tor proxy (``self.reuse == True``).
        """

        if not self.reuse:
            self.process.kill()
        else:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
