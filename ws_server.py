import asyncio
import websockets
import json

clients = set()

async def register(websocket):
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)

async def handler(websocket, path):
    await register(websocket)
    async for message in websocket:
        print(f"Received: {message}")
        for client in clients:
            if client != websocket:
                await client.send(message)

start_server = websockets.serve(handler, "localhost", 8765)

print("WebSocket server started on ws://localhost:8765")
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
