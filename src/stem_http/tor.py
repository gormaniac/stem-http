"""Manage the Tor proxy."""

import subprocess
from typing import Optional

import stem
import stem.control
import stem.process


BIND_FAIL_MSG = "Failed to bind one of the listener ports."
BROKEN_CONF_MSG = "Acting on config options left us in a broken state. Dying."


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
        - When reusing a proxy fails and ``exit_on_reuse_fail`` is ``True``.
        - When there's already a Tor proxy running on this host or there's a config error.
        - When there's been too many retries while starting a new Tor process.
    OSError
        When ever there's an error starting the Tor process.
        See the ``log_file`` for details.
    """

    def __init__(
        self,
        reuse: bool = False,
        retry: bool = True,
        country: Optional[str] = None,
        passw: Optional[str] = None,
        socks_port: int = 9050,
        cntrl_port: int = 9051,
        exit_on_reuse_fail: bool = False,
        log_file: Optional[str] = "/tmp/tor_log",
        tor_debug: bool = False,
    ) -> None:
        self.log_level = "DEBUG" if tor_debug else "NOTICE"
        self.tor_log = log_file

        self.cntrl_passw = passw
        self.reuse = reuse
        self.retry = retry
        self.country = country

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

    def start(self, retries: int = 10):
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

        tor_conf = {
            "ControlPort": str(self.cntrl_port),
            "SocksPort": str(self.socks_port),
        }

        if self.tor_log:
            tor_conf["Log"] = [
                f"{self.log_level} file {self.tor_log}",
            ]

        if self.country:
            tor_conf["ExitNodes"] = "{%s}" % self.country

        try:
            self.process: subprocess.Popen = stem.process.launch_tor_with_config(
                config=tor_conf,
                take_ownership=True,
            )
        except OSError as err:
            if BIND_FAIL_MSG in str(err) and self.retry and retries > 0:
                self._bump_ports()
                # TODO - Make retries configurable? This limits number of instances.
                retries -= 1
                self.start(retries=retries)
            elif BROKEN_CONF_MSG in str(err):
                raise RuntimeError(
                    "Config error, there might be another instance of Tor running! "
                    f"Try using the 'reuse' arg.\n{err}"
                ) from err
            elif retries == 0:
                raise RuntimeError("Max number of ProxyMgr retries reached!") from err
            else:
                raise err

    def _bump_ports(self):
        self.socks_port += 2
        self.cntrl_port += 2

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
