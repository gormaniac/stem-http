"""Manage the Tor proxy."""

import subprocess

import stem.control
import stem.process


class ProxyMgr:
    """Manages a Tor Proxy process attached to the calling process."""

    def __init__(self) -> None:
        self.socks_port = 9050
        self.cntrl_port = 9051
        self.process: subprocess.Popen = stem.process.launch_tor_with_config(
            config={
                "ControlPort": str(self.cntrl_port),
                "SocksPort": str(self.socks_port),
            },
            take_ownership=True,
        )

        self.proxy_url = f"socks5://127.0.0.1:{self.socks_port}"

    def stop(self):
        """Kill the tor process.
        
        Must be done before exiting Python or the tor process may persist.
        """

        self.process.kill()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
