# ws_server.py
import asyncio
import websockets
import json

connected_clients = set()

async def register_client(websocket):
    connected_clients.add(websocket)

async def unregister_client(websocket):
    connected_clients.remove(websocket)

async def websocket_handler(websocket, path):
    # Register client
    await register_client(websocket)
    try:
        async for message in websocket:
            # Handle incoming messages
            data = json.loads(message)
            # Process data or send messages
    finally:
        # Unregister client on disconnect
        await unregister_client(websocket)

def start_server():
    return websockets.serve(websocket_handler, "0.0.0.0", 5678)

# main.py
import asyncio
from ws_server import start_server

# Your other application code here...

async def main_logic():
    # Your main logic...
    pass

async def main():
    server = start_server()
    await asyncio.gather(
        server,
        main_logic(),
    )

if __name__ == '__main__':
    asyncio.run(main())
