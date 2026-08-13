import asyncio
import json
import logging
import os
import random
import signal
import sys
from typing import List

import websockets
import socketio

from backend.strategy import EMAStrategy

# Config
DERIV_WS_URL = os.environ.get("DERIV_WS_URL", "wss://ws.binaryws.com/websockets/v3")
API_TOKEN = os.environ.get("API_TOKEN")
SYMBOLS = [s.strip() for s in os.environ.get("SYMBOLS", "R_100").split(",") if s.strip()]
LOG_PATH = os.environ.get("LOG_PATH")  # optional path to save logs
SIGNAL_SERVER_URL = os.environ.get("SIGNAL_SERVER_URL", "http://localhost:5000")

# Reconnect/backoff settings
BACKOFF_BASE = 1.0
BACKOFF_MAX = 60.0

# Graceful shutdown
shutdown = False

sio = socketio.AsyncClient(reconnection=True, logger=False, engineio_logger=False)


def setup_logging():
    level = os.environ.get("LOG_LEVEL", "INFO")
    log_level = getattr(logging, level.upper(), logging.INFO)
    handlers = [logging.StreamHandler(sys.stdout)]
    if LOG_PATH:
        from logging.handlers import RotatingFileHandler

        handlers.append(RotatingFileHandler(LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=3))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def _on_signal(signum, frame):
    global shutdown
    logging.info("Signal %s received, shutting down...", signum)
    shutdown = True


async def ensure_sio_connected():
    """Ensure the socketio client is connected to the backend web server to publish signals."""
    if sio.connected:
        return
    try:
        logging.info("Connecting to signal server %s", SIGNAL_SERVER_URL)
        await sio.connect(SIGNAL_SERVER_URL, transports=["websocket"])  # uses socket.io path
        logging.info("Connected to signal server")
    except Exception as e:
        logging.warning("Could not connect to signal server: %s", e)


async def authorize(ws: websockets.WebSocketClientProtocol):
    if not API_TOKEN:
        logging.info("No API_TOKEN set; proceeding without authorization (public endpoints only).")
        return

    msg = {"authorize": API_TOKEN}
    await ws.send(json.dumps(msg))
    resp = await ws.recv()
    logging.info("Authorize response: %s", resp)


async def subscribe_ticks(ws: websockets.WebSocketClientProtocol, symbols: List[str]):
    for s in symbols:
        req = {"ticks": s, "subscribe": 1}
        await ws.send(json.dumps(req))
        logging.info("Sent subscribe request for %s", s)


async def consume(ws: websockets.WebSocketClientProtocol, strategy: EMAStrategy, symbol: str):
    async for message in ws:
        # Here you can parse, validate, and route messages to storage, metrics, etc.
        try:
            data = json.loads(message)
        except Exception:
            logging.info("Raw message: %s", message)
            continue

        # Process ticks
        if "tick" in data and data.get("tick"):
            tick = data["tick"]
            # run strategy
            try:
                result = strategy.process_tick(tick)
                # attach symbol
                result["symbol"] = symbol
                logging.info("Signal: %s", json.dumps(result))
                # send to signal server if connected
                try:
                    await ensure_sio_connected()
                    if sio.connected:
                        await sio.emit("signal", result)
                except Exception as e:
                    logging.warning("Failed to emit signal to server: %s", e)
            except Exception as e:
                logging.exception("Strategy error: %s", e)
        elif "error" in data:
            logging.error("Deriv error: %s", data.get("error"))
        else:
            logging.debug("Message: %s", json.dumps(data))

        if shutdown:
            break


async def run_once(symbols: List[str], strategy: EMAStrategy):
    global shutdown
    async with websockets.connect(DERIV_WS_URL, ping_interval=20, ping_timeout=20) as ws:
        logging.info("Connected to %s", DERIV_WS_URL)
        # Authorize if token provided
        await authorize(ws)
        # Subscribe to symbols
        await subscribe_ticks(ws, symbols)
        # Consume messages until shutdown
        try:
            # we assume only one symbol subscription per connection for strategy state clarity; consume handles ticks
            await consume(ws, strategy, symbols[0])
        except websockets.ConnectionClosed as e:
            logging.warning("Connection closed: %s", e)
            raise


async def worker_loop():
    backoff = BACKOFF_BASE
    symbols = SYMBOLS if SYMBOLS else ["R_100"]

    # create a strategy per symbol (currently only uses the first symbol's strategy)
    strategy = EMAStrategy()

    # Attempt to connect sio in background
    await ensure_sio_connected()

    while not shutdown:
        try:
            await run_once(symbols, strategy)
            # reset backoff after a clean connection
            backoff = BACKOFF_BASE
        except Exception as exc:
            logging.exception("Worker error: %s", exc)
            if shutdown:
                break
            sleep_for = backoff + random.random()
            logging.info("Reconnecting in %.1f seconds...", sleep_for)
            await asyncio.sleep(sleep_for)
            backoff = min(backoff * 2, BACKOFF_MAX)

    logging.info("Worker loop exiting.")
    # disconnect sio
    try:
        if sio.connected:
            await sio.disconnect()
    except Exception:
        pass


def main():
    if not API_TOKEN:
        logging.warning("API_TOKEN is not set. The worker will still attempt public subscriptions if supported.")

    setup_logging()

    # Signal handling for graceful shutdown
    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    logging.info("Starting Deriv streaming worker. Symbols: %s", ",".join(SYMBOLS))

    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received, exiting")


if __name__ == "__main__":
    main()
