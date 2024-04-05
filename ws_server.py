import asyncio
import websockets
import json

connected_clients = set()

async def register_client(websocket):
    print("Client Connected!")
    connected_clients.add(websocket)

async def unregister_client(websocket):
    print("Client Disconnected!")

    connected_clients.remove(websocket)

async def send_coordinates(x, y):
    message = json.dumps({'x': x, 'y': y})
    if connected_clients:  # Check if there are any connected clients
        tasks = [asyncio.create_task(client.send(message)) for client in connected_clients]
        await asyncio.wait(tasks)

async def websocket_handler(websocket, path):
    await register_client(websocket)
    try:
        async for message in websocket:
            print(f"Received message: {message}")
            data = json.loads(message)
            x, y = data['x'], data['y']
            await send_coordinates(x, y)  # Broadcast the coordinates to all connected clients
    finally:
        await unregister_client(websocket)

async def main():
    try:
        async with websockets.serve(websocket_handler, "localhost", 5678):
            print("WebSocket server started on ws://localhost:5678")
            await asyncio.Future()  # Run the server forever
    except KeyboardInterrupt:
        print("WebSocket server stopped")

    

if __name__ == '__main__':
    asyncio.run(main())
