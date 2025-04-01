import asyncio
from typing import Dict, List, Callable, Any, Coroutine
import logging
import threading

logger = logging.getLogger(__name__)

class MessageBroker:
    """
    A simple message broker that allows agents to publish messages
    and the API to subscribe to these messages.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MessageBroker, cls).__new__(cls)
            cls._instance._subscribers = {}
            cls._instance._event_loop = None
            cls._instance._pending_messages = []
            cls._instance._thread_local = threading.local()
        return cls._instance
    
    def __init__(self):
        self._subscribers = {}
        self._event_loop = None
        self._pending_messages = []
        self._thread_local = threading.local()
    
    def set_event_loop(self, loop):
        """Set the event loop for async operations"""
        self._event_loop = loop
        
        # Process any pending messages
        if self._pending_messages:
            logger.info(f"Processing {len(self._pending_messages)} pending messages")
            for event_type, data in self._pending_messages:
                self.publish(event_type, data)
            self._pending_messages = []
    
    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], Coroutine]):
        """
        Subscribe to a specific event type
        
        Args:
            event_type: The type of event to subscribe to
            callback: The async callback function to call when the event occurs
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed to event type: {event_type}")
    
    def publish(self, event_type: str, data: Dict[str, Any]):
        """
        Publish an event to all subscribers
        
        Args:
            event_type: The type of event to publish
            data: The data to send with the event
        """
        if not self._event_loop:
            # Store the message for later processing
            self._pending_messages.append((event_type, data))
            logger.warning(f"Event loop not set. Message queued for later: {event_type}")
            return
        
        try:
            # Try to get the current event loop
            current_loop = asyncio.get_event_loop()
        except RuntimeError:
            # If we're in a different thread without an event loop, store the message
            self._pending_messages.append((event_type, data))
            logger.warning(f"No event loop in current thread. Message queued for later: {event_type}")
            return
        
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                if current_loop == self._event_loop:
                    # If we're in the main event loop, create a task
                    asyncio.create_task(callback(data))
                else:
                    # If we're in a different thread with its own event loop, use run_coroutine_threadsafe
                    future = asyncio.run_coroutine_threadsafe(callback(data), self._event_loop)
                    # Add a callback to handle any exceptions
                    future.add_done_callback(lambda f: logger.error(f"Error in event callback: {f.exception()}") if f.exception() else None)
                
                logger.info(f"Published event: {event_type}")
        else:
            logger.warning(f"No subscribers for event type: {event_type}")

# Create a singleton instance
message_broker = MessageBroker()