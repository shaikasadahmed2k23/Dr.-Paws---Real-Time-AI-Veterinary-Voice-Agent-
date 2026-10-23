# Friction Log: Dr. Paws MCP server (Amazon Build, Ship, Shape 2026, Alexa+ track)

## 1. FastMCP import fails on MCP Python SDK v2
- **Task:** Create an MCP server with the familiar `from mcp.server.fastmcp import FastMCP`.
- **Steps:** `pip install -U "mcp[cli]"` (installed 2.3.0), ran the server.
- **Expected:** Server starts, as in most MCP / Alexa+ MCP tutorials.
- **Actual:** `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`. In v2, FastMCP is renamed to `MCPServer` (`from mcp.server.mcpserver import MCPServer`).
- **Severity:** High (blocks hello-world for anyone following existing tutorials).
- **Workaround:** Switched to `MCPServer`, following the error's migration link.
- **Suggestion:** Alexa+ MCP docs and samples should pin an SDK version or show the v2 import, so first-time builders don't hit this in minute one.

## 2. Client helper and field names renamed in v2
- **Task:** Write a test client for the Streamable HTTP endpoint.
- **Steps:** Used `streamablehttp_client` and `init.protocolVersion` from v1 examples.
- **Expected:** Client connects and prints the negotiated protocol.
- **Actual:** `ImportError` (now `streamable_http_client`), then `AttributeError` (now `protocol_version`, `server_info`, `structured_content`).
- **Severity:** Medium.
- **Workaround:** Renamed to the snake_case v2 API.
- **Suggestion:** Provide an official minimal Alexa+ MCP test client (server + client in one repo) for the current SDK.

## 3. DNS-rebinding protection vs. hosted deployment
- **Task:** Expose the server publicly (Render) so an MCP client can reach `/mcp`.
- **Expected:** A clear default for a public host.
- **Actual:** Host-header validation needs explicit `TransportSecuritySettings(allowed_hosts=[...])` configuration for a public hostname.
- **Severity:** Medium.
- **Workaround:** Made it env-driven (`MCP_ALLOWED_HOSTS`): protection on with the listed hosts, off for local testing.
- **Suggestion:** The Alexa+ MCP guide should include a "deploying your MCP server publicly" checklist (host allowlist, HTTPS, stateless mode).

## 4. No way to test against real Alexa+ without Preview access
- **Task:** Verify the MCP server end to end on an actual Alexa+ device.
- **Expected:** A sandbox or simulator that connects to a self-hosted MCP URL.
- **Actual:** Testing was limited to MCP Inspector and a Python MCP client.
- **Severity:** Important.
- **Workaround:** Designed every tool to return a short `voice_response` so output is already shaped for speech.
- **Suggestion:** An Alexa+ MCP simulator (paste MCP URL, talk to it in the browser) would let developers validate the voice UX before Preview access.
