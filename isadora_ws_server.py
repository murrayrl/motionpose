#!/usr/bin/env python3
import asyncio
import websockets

# Websocket server handler
async def handler(websocket, path):
    async for message in websocket:
        print("Received JSON from Pi:", message)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("Websocket server running on ws://0.0.0.0:8765")
        await asyncio.Future()  # keep server alive

if __name__ == "__main__":
    asyncio.run(main())
