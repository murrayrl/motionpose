# Import necessary libraries
import asyncio  # Asyncio library for asynchronous programming
import websockets  # Websockets library for creating WebSocket servers
import json  # JSON library for parsing JSON messages

# Define the WebSocket handler function, which will manage client connections
async def handler(websocket, path):
    print("Client connected")  # Print a message when a client connects
    try:
        # Continuously listen for messages from the connected WebSocket client
        async for message in websocket:
            # Parse the incoming message from JSON format to a Python dictionary
            data = json.loads(message)
            
            # Print the received data in a structured format
            print("Received data:")
            print("  Coordinates:", data.get("coordinate"))  # Access the 'coordinate' field from the data
            print("  Body Part:", data.get("bodyPart"))      # Access the 'bodyPart' field
            print("\n")  # Print a newline for readability between messages
    except websockets.ConnectionClosed:
        # Handle the case where the client disconnects
        print("Client disconnected")

# Main function to set up and run the WebSocket server
async def main():
    # Create the WebSocket server and bind it to localhost on port 6789
    async with websockets.serve(handler, "localhost", 6789):
        print("WebSocket server running on ws://localhost:6789")  # Log server start
        await asyncio.Future()  # Keep the server running indefinitely

# Entry point of the script
if __name__ == "__main__":
    # Run the main function using asyncio's event loop
    asyncio.run(main())