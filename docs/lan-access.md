# LAN Access

Start the LAN launcher:

```bash
./run-lan.sh
```

It binds the app server to `0.0.0.0`. Open the printed network URL from another device on the same trusted network.

LAN mode exposes the UI to other devices that can reach the host. Do not use it on an untrusted network, and do not expose the port directly to the public internet.

Override the host or port with `TRADINGAGENTS_UI_HOST` and `TRADINGAGENTS_UI_PORT`.
