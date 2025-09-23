import asyncio
import websockets

# ────────────────────────────────
# EDIT THESE VALUES
# ────────────────────────────────
IP   = "0.0.0.0"   # "0.0.0.0" = listen on all interfaces, or set to your PC's IP
PORT = 8765        # Port to listen on (must match what Pi script connects to)
# ────────────────────────────────

async def handler(websocket, path):
    async for message in websocket:
        print("Received JSON from Pi:", message)

async def main():
    async with websockets.serve(handler, IP, PORT):
        print(f"WebSocket server running on ws://{IP}:{PORT}")
        await asyncio.Future()  # keep server alive

if __name__ == "__main__":
    asyncio.run(main())
