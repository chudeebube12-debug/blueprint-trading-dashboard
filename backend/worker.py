import os
import time
import signal
import sys

API_TOKEN = os.environ.get("API_TOKEN")


def _shutdown(signum, frame):
    print("Shutdown signal received, exiting.")
    sys.exit(0)


def main():
    if not API_TOKEN:
        print("API_TOKEN not set — worker will exit.")
        return

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    print("Deriv worker starting (placeholder).")
    print("API_TOKEN set:", 'yes' if API_TOKEN else 'no')

    # Replace this loop with real Deriv streaming logic
    try:
        while True:
            print("Worker heartbeat — connect to Deriv API here")
            # Example place: open websocket, authenticate with API_TOKEN, stream ticks, handle reconnects
            time.sleep(30)
    except SystemExit:
        print("Worker exiting cleanly.")
    except Exception as e:
        print("Worker error:", e)
        # Optionally add retry/backoff here


if __name__ == "__main__":
    main()
