import asyncio
import websockets
import json

async def receive_coordinates(websocket):
    try:
        while True:
            data = await websocket.recv()
            print("Received data:", data)  # Check if data is received
            coordinates = json.loads(data)
            print(f"Received coordinates: Distance: {coordinates['distance']}, X: {coordinates['x']}, Y: {coordinates['y']}")
    except Exception as e:
        print(f"Error: {e}")
        
async def main():
    async with websockets.connect("ws://localhost:5678") as websocket:
        await receive_coordinates(websocket)

if __name__ == "__main__":
    asyncio.run(main())
