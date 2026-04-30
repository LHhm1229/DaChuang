import asyncio
import websockets

WS_URL = "ws://localhost:3001/ws"

async def main():
    print("Connecting:", WS_URL)
    try:
        async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
            print("✅ connected, waiting messages...\n")
            while True:
                msg = await ws.recv()
                print("WS:", msg)
    except Exception as e:
        print("❌ ws client error:", repr(e))

if __name__ == "__main__":
    asyncio.run(main())
