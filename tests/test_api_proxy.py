"""NBA.com blocks datacenter IPs, so blocked networks must reach the API through
a proxy. These tests pin the proxy plumbing: it is off by default, it is driven
by the ``NBA_STATS_PROXY`` secret, and when configured it actually routes both
nba_api endpoint traffic and the module's direct requests through the proxy.

The routing test uses a throwaway local proxy that records the CONNECT target,
which proves traffic is tunnelled to ``stats.nba.com`` without needing real
(unblocked) NBA access.
"""
from __future__ import annotations

import importlib
import socket
import threading
from unittest.mock import MagicMock, patch

import pytest

import nba_api.library.http as nba_http
from bulls.data import fetch


@pytest.fixture
def clean_proxy_env(monkeypatch):
    """Remove every proxy variable so a test starts from a known 'direct' state."""
    for name in ("NBA_STATS_PROXY", "HTTPS_PROXY", "https_proxy"):
        monkeypatch.delenv(name, raising=False)
    yield


def test_no_proxy_is_configured_by_default():
    """A laptop on home internet reaches NBA directly; the default must be off."""
    assert fetch.NBA_PROXY == ""
    assert fetch._PROXIES is None
    assert nba_http.PROXY == ""


def test_dedicated_secret_wins_over_https_proxy(clean_proxy_env, monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://fallback:8080")
    monkeypatch.setenv("NBA_STATS_PROXY", "http://dedicated:9000")
    assert fetch._resolve_proxy() == "http://dedicated:9000"


def test_https_proxy_is_honoured_as_a_fallback(clean_proxy_env, monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://fallback:8080")
    assert fetch._resolve_proxy() == "http://fallback:8080"


def test_blank_or_missing_proxy_means_direct(clean_proxy_env, monkeypatch):
    assert fetch._resolve_proxy() == ""
    monkeypatch.setenv("NBA_STATS_PROXY", "   ")
    assert fetch._resolve_proxy() == ""


def test_configuring_the_module_sets_both_transports(clean_proxy_env, monkeypatch):
    """Reloading with the secret set must arm nba_api and the direct-request path."""
    monkeypatch.setenv("NBA_STATS_PROXY", "http://proxy.example:7000")
    saved = nba_http.PROXY
    try:
        importlib.reload(fetch)
        assert fetch.NBA_PROXY == "http://proxy.example:7000"
        assert fetch._PROXIES == {
            "http": "http://proxy.example:7000",
            "https": "http://proxy.example:7000",
        }
        assert nba_http.PROXY == "http://proxy.example:7000"
    finally:
        nba_http.PROXY = saved
        monkeypatch.delenv("NBA_STATS_PROXY", raising=False)
        importlib.reload(fetch)  # restore the direct (no-proxy) module state


def _capture_proxy():
    """A one-shot local proxy that records the first request line, then closes.

    Returns ``(url, get_connect_line)``. ``get_connect_line`` blocks briefly for
    the captured line so the test can assert what the client asked to tunnel to.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    captured: list[str] = []

    def serve():
        try:
            conn, _ = server.accept()
            with conn:
                data = conn.recv(4096).decode("latin-1", "replace")
                captured.append(data.splitlines()[0] if data else "")
                conn.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        except OSError:
            pass
        finally:
            server.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    def get_connect_line() -> str:
        thread.join(timeout=8)
        return captured[0] if captured else ""

    return f"http://127.0.0.1:{port}", get_connect_line


def test_nba_api_endpoint_routes_through_the_configured_proxy():
    """The load-bearing proof: an nba_api call tunnels to stats.nba.com via proxy."""
    from nba_api.stats.endpoints import commonteamroster

    proxy_url, get_connect_line = _capture_proxy()
    saved = nba_http.PROXY
    nba_http.PROXY = proxy_url
    try:
        with pytest.raises(Exception):
            # The capture proxy refuses the tunnel, so this must fail -- but only
            # after the CONNECT reaches the proxy, which is what we assert.
            commonteamroster.CommonTeamRoster(
                team_id=fetch.BULLS_TEAM_ID, season=fetch.CURRENT_SEASON,
                timeout=3,
            )
    finally:
        nba_http.PROXY = saved

    connect_line = get_connect_line()
    assert connect_line.startswith("CONNECT stats.nba.com:443"), connect_line


def test_direct_headshot_fetch_uses_the_proxies_mapping(monkeypatch, tmp_path):
    sentinel = {"http": "http://p:1", "https": "http://p:1"}
    monkeypatch.setattr(fetch, "_PROXIES", sentinel)

    resp = MagicMock()
    resp.content = b"img-bytes"
    resp.raise_for_status = MagicMock()
    with patch("bulls.data.fetch.requests.get", return_value=resp) as mock_get:
        fetch.get_player_headshot(1629632, cache_dir=str(tmp_path))

    assert mock_get.call_args.kwargs["proxies"] is sentinel


def test_direct_roster_fetch_uses_the_proxies_mapping(monkeypatch):
    sentinel = {"http": "http://p:1", "https": "http://p:1"}
    monkeypatch.setattr(fetch, "_PROXIES", sentinel)

    resp = MagicMock()
    resp.text = '<html>"roster":[{"PLAYER_ID":1,"PLAYER":"Test Player"}]</html>'
    resp.raise_for_status = MagicMock()
    with patch("bulls.data.fetch.requests.get", return_value=resp) as mock_get:
        roster = fetch.get_current_roster()

    assert mock_get.call_args.kwargs["proxies"] is sentinel
    assert roster.iloc[0]["official_roster_name"] == "Test Player"
