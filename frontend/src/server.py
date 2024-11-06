import asyncio
import websockets
import json

async def handler(websocket, path):
    print("Client connected")
    try:
        async for message in websocket:
            data = json.loads(message)
            print("Received data:")
            print("  Coordinates:", data.get("coordinate"))
            print("  Body Part:", data.get("bodyPart"))
            print("  Direction:", data.get("direction"))
            print("\n")
    except websockets.ConnectionClosed:
        print("Client disconnected")

async def main():
    async with websockets.serve(handler, "localhost", 6789):
        print("WebSocket server running on ws://localhost:6789")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())