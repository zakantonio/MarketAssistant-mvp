from enum import Enum
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import JSONResponse
import uvicorn
import uuid
import json
from typing import Dict, Optional, Any
import logging
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import tempfile
import os
import sys
import asyncio
import base64
import requests
from typing import Dict, Optional, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.agent_manager import AgentManager
from utils.AudioTranscriber import AudioTranscriber
from utils.message_broker import message_broker

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define DATABASE_URL before any potential imports that might need it
DATABASE_URL = os.environ.get("DATABASE_URL")

# Store active connections with their unique IDs
active_connections: Dict[str, WebSocket] = {}

# Connection manager to handle WebSocket connections
class WebSocketConnectionManager:
    def __init__(self):
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_tasks = {}  # Store heartbeat tasks by client_id
    
    async def connect(self, websocket: WebSocket) -> str:
        """
        Connect a new WebSocket client and return a unique client ID
        """
        await websocket.accept()
        client_id = str(uuid.uuid4())
        active_connections[client_id] = websocket
        logger.info(f"Client connected: {client_id}")
        
        # Start heartbeat for this connection
        self.heartbeat_tasks[client_id] = asyncio.create_task(
            self._heartbeat_client(client_id, websocket)
        )
        
        return client_id

    async def disconnect(self, client_id: str):
        """
        Disconnect a client and remove from active connections
        """
        if client_id in active_connections:
            del active_connections[client_id]
            logger.info(f"Client disconnected: {client_id}")
            
        # Cancel heartbeat task if exists
        if client_id in self.heartbeat_tasks:
            self.heartbeat_tasks[client_id].cancel()
            del self.heartbeat_tasks[client_id]
            
    async def _heartbeat_client(self, client_id: str, websocket: WebSocket):
        """
        Send periodic pings to check if client is still connected
        """
        try:
            while client_id in active_connections:
                await asyncio.sleep(self.heartbeat_interval)
                try:
                    # Instead of using ping(), send a JSON message as heartbeat
                    await websocket.send_json({
                        "type": "heartbeat",
                        "client_id": client_id
                    })
                    logger.debug(f"Heartbeat sent to client: {client_id}")
                except (WebSocketDisconnect, ConnectionResetError, RuntimeError) as e:
                    logger.warning(f"Heartbeat failed for client {client_id}: {str(e)}")
                    # Client connection is broken, consider it disconnected
                    await self.disconnect(client_id)
                    break
        except asyncio.CancelledError:
            # Task was cancelled, just exit
            pass
        except Exception as e:
            logger.error(f"Error in heartbeat for client {client_id}: {str(e)}")
            await self.disconnect(client_id)

    async def send_response(self, client_id: str, msg_type: str, message: str):
        """
        Send a response to a specific client via message broker
        """
        # Use message broker instead of direct WebSocket communication
        message_broker.publish(
            "websocket_message",
            {"client_id": client_id, "type": msg_type, "content": message},
        )
        logger.info(f"Response queued for client: {client_id}")

    async def handle_agent_message(self, data: Dict[str, Any]):
        """
        Handle messages from agents via the message broker
        """
        client_id = data.get("client_id")
        message_type = data.get("type", "agent_update")
        content = data.get("content", "")

        if client_id in active_connections:
            websocket = active_connections[client_id]

            # Handle different message types
            if message_type == "direct_message":
                # Send raw message content as text
                await websocket.send_text(content)
                logger.info(f"Direct message sent to client: {client_id}")
            else:
                # Send structured JSON for other message types
                await websocket.send_json(
                    {"type": message_type, "content": content, "client_id": client_id}
                )
                logger.info(f"Agent message sent to client: {client_id}")
        else:
            logger.warning(f"Client not found for message: {client_id}")


# Initialize the connection manager first
manager = WebSocketConnectionManager()

# Replace deprecated @app.on_event with lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup - runs before application starts
    # Set the event loop for the message broker
    message_broker.set_event_loop(asyncio.get_running_loop())

    # Subscribe to agent messages - use handle_agent_message for all message types
    message_broker.subscribe("agent_message", manager.handle_agent_message)
    message_broker.subscribe("agent_progress", manager.handle_agent_message)
    message_broker.subscribe("agent_error", manager.handle_agent_message)
    message_broker.subscribe("websocket_message", manager.handle_agent_message)

    yield

    # Cleanup - runs when application is shutting down
    # Any cleanup code would go here

app = FastAPI(title="Market Assistant API", lifespan=lifespan)

origins = ["*"]  # Allow all origins (for development only)

# Aggiungi questa configurazione dopo la creazione dell'app FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize other components after FastAPI app is created
agent_manager = AgentManager()
transcriber = AudioTranscriber()

class EventType(Enum):
    AUDIO_RECEIVED = "audio_received"
    TEXT_RECEIVED = "text_received"
    PROCESSING = "processing"
    REPLYING = "replying"
    NOT_FOUND = "errornotfound"


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = await manager.connect(websocket)

    # Send client ID to the client for future reference
    await websocket.send_json(
        {"client_id": client_id, "message": "Connected to Market Assistant"}
    )

    try:
        while True:
            # Wait for messages from the client with a timeout
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), 
                    timeout=120  # 2 minute timeout for receiving messages
                )
                
                try:
                    # Parse the received JSON data
                    request_data = json.loads(data)
                    request_type = request_data.get("type")
                    content = request_data.get("content")

                    # Handle ping messages from client
                    if request_type == "ping" or request_type == "heartbeat":
                        await websocket.send_json({
                            "type":  "pong" if request_type == "ping" else "heartbeat_ack", 
                            "client_id": client_id
                        })
                        continue

                    if request_type == "text":
                        # Process text input
                        logger.info(
                            f"Received text from client {client_id}: {content[:50]}..."
                        )

                        await send_event(client_id, EventType.TEXT_RECEIVED)

                        await process_text_task(content, client_id)

                    elif request_type == "audio":
                        # Process audio input (base64 encoded)
                        logger.info(f"Received audio from client {client_id}")

                        await send_event(client_id, EventType.AUDIO_RECEIVED)

                        try:
                            # Decode base64 audio data before writing to file
                            audio_bytes = base64.b64decode(content)

                            await process_audio_task(audio_bytes, client_id)

                        except Exception as e:
                            logger.error(f"Error processing audio: {str(e)}")
                            await send_message(
                                client_id, "error", f"Error processing audio: {str(e)}"
                            )
                    else:
                        # Unknown request type
                        await send_message(
                            client_id, "error", f"Unknown request type: {request_type}"
                        )

                except json.JSONDecodeError:
                    # Handle invalid JSON
                    await send_message(client_id, "error", "Invalid JSON format")
                    
            except asyncio.TimeoutError:
                # No message received within timeout, check if client is still connected
                try:
                    # Send a JSON heartbeat instead of ping frame
                    await websocket.send_json({
                        "type": "connection_check",
                        "client_id": client_id
                    })
                    logger.debug(f"Connection check sent to client: {client_id}")
                    # If we get here, the connection is still alive
                except Exception as e:
                    # Client connection is broken, consider it disconnected
                    logger.warning(f"Client {client_id} timed out and didn't respond: {str(e)}")
                    break

    except WebSocketDisconnect:
        # Handle client disconnection
        await manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"Error in websocket connection for client {client_id}: {str(e)}")
        await manager.disconnect(client_id)


# REST endpoint for clients that can't use WebSockets
@app.post("/api/text")
async def process_text(
    text: str = Form(...), client_id: Optional[str] = Form(None), debug: bool = False
):
    """
    Process text input via REST API
    """
    logger.info(f"Received text via REST API: {text[:50]}...")

    # Generate a client ID if not provided
    if not client_id or client_id not in active_connections:
        return JSONResponse(
            status_code=400,
            content={"error": "Valid client_id required. Connect via WebSocket first."},
        )

    # Return immediate response
    response_task = JSONResponse(
        content={"status": "processing", "client_id": client_id}
    )

    # Start background task
    asyncio.create_task(process_text_task(text, client_id))

    return response_task


@app.post("/api/audio")
async def process_audio(
    audio: UploadFile = File(...), client_id: Optional[str] = Form(None)
):
    """
    Process audio input via REST API
    """
    logger.info(f"Received audio file via REST API: {audio.filename}")

    # Generate a client ID if not provided
    if not client_id or client_id not in active_connections:
        return JSONResponse(
            status_code=400,
            content={"error": "Valid client_id required. Connect via WebSocket first."},
        )

    # Read the audio file content
    audio_content = await audio.read()

    # Return immediate response
    response_task = JSONResponse(
        content={"status": "processing", "client_id": client_id}
    )

    # Start background task
    asyncio.create_task(process_audio_task(audio_content, client_id))

    return response_task


@app.get("/")
async def root():
    return {
        "message": "Market Assistant API. Connect to /ws for WebSocket communication."
    }


# Create background task for processing
async def process_text_task(text: str, client_id: str):
    # Send processing event
    await send_event(client_id, EventType.PROCESSING)
    
    # Allow event loop to process the event
    await asyncio.sleep(0)
    
    # Use run_in_executor to prevent blocking the event loop
    response = await asyncio.get_event_loop().run_in_executor(
        None, lambda: agent_manager.route_query(text, client_id)
    )
    
    text_response = response["text"]
    results = response["results"]

    if results:
        # Send table response
        await send_message(client_id, "table_response", results)
    
        # Allow event loop to process the event
        await asyncio.sleep(0)
    else:
        # Send error response
        await send_event(client_id, EventType.NOT_FOUND)
        return

    # Send replying event
    await send_event(client_id, EventType.REPLYING)
    
    # Allow event loop to process the event
    await asyncio.sleep(0)
    
    if text_response:
        # Send text response
        await send_message(client_id, "text_response", text_response)
    
        # Allow event loop to process the event
        await asyncio.sleep(0)

async def process_audio_task(audio_content, client_id):
    try:
        # Save audio content to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio_content)
            temp_audio_path = temp_audio.name

        try:
            # Process the audio using the transcriber
            transcription = transcriber.transcribe(temp_audio_path)

            logger.info(f"Transcription: {transcription}")

            # Send the transcription to the agent manager
            await process_text_task(transcription, client_id)

        finally:
            # Clean up the temporary file
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)

    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        await send_message(client_id, "error", f"Error processing audio: {str(e)}")

async def send_message(client_id: str, msg_type: str, message: str):
    await manager.send_response(client_id, msg_type, message)

async def send_event(client_id, event: EventType):
    await manager.send_response(client_id, "event_response", event.value)

# Add new endpoints for log dashboard
@app.get("/dashboard/logs/")
async def get_logs(limit: int = 1000):
    """
    Proxy endpoint to fetch logs from the product API
    """
    try:
        response = requests.get(f"{DATABASE_URL}/logs/?limit={limit}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching logs: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to fetch logs: {str(e)}"}
        )

@app.get("/dashboard/logs/stats")
async def get_logs_stats():
    """
    Proxy endpoint to fetch log statistics from the product API
    """
    try:
        response = requests.get(f"{DATABASE_URL}/logs/stats")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching log stats: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to fetch log statistics: {str(e)}"}
        )

if __name__ == "__main__":
    uvicorn.run(
        "api:app", host="0.0.0.0", port=int(os.environ.get("API_PORT", 8101)), reload=True
    )
