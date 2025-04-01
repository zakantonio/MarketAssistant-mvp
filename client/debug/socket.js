/**
 * Market Assistant WebSocket Client
 * This script manages the WebSocket connection with the Market Assistant server
 * and processes the received messages.
 */
class MarketAssistantClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.socket = null;
    this.clientId = null;
    this.listeners = {
      text_response: [],
      audio_response: [],
      event_response: [], // Added event_response listener
      table_response: [],
      error: [],
      connect: [],
      disconnect: []
    };
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectInterval = 3000;
    this.reconnectTimer = null;
    this.pingInterval = null;
  }

  /**
   * Initializes the WebSocket connection
   */
  connect() {
    return new Promise((resolve, reject) => {
      try {
        console.log(`Connection attempt to ${this.baseUrl}/ws`);
        this.socket = new WebSocket(`${this.baseUrl}/ws`);
        
        // Update connection status in console
        console.log('Connection in progress...');

        this.socket.onopen = () => {
          console.log('WebSocket connected');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this._notifyListeners('connect', { status: 'connected' });
          
          // Start ping interval to keep connection alive
          this._startPingInterval();
        };

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('Message received:', data);

            // Save the client_id when we receive it from the server
            if (data.client_id && !this.clientId) {
              this.clientId = data.client_id;
              resolve(this.clientId);
            }

            // Notify listeners based on message type
            if (data.type) {
              this._notifyListeners(data.type, data);
            }
          } catch (error) {
            console.error('Error parsing message:', error);
            this._notifyListeners('error', { 
              error: 'Error parsing message', 
              details: error.message 
            });
          }
        };

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          this._notifyListeners('error', { 
            error: 'WebSocket connection error', 
            details: error 
          });
          reject(error);
        };

        this.socket.onclose = (event) => {
          console.log('WebSocket disconnected', event.code, event.reason);
          this.isConnected = false;
          this._stopPingInterval();
          this._notifyListeners('disconnect', { 
            status: 'disconnected', 
            code: event.code, 
            reason: event.reason 
          });
          
          // Attempt to reconnect if not a normal closure
          if (event.code !== 1000 && event.code !== 1001) {
            this._attemptReconnect();
          } else {
            this.clientId = null;
          }
        };
      } catch (error) {
        console.error('Error creating WebSocket connection:', error);
        reject(error);
      }
    });
  }
  
  /**
   * Attempts to reconnect to the WebSocket server with exponential backoff
   * @private
   */
  _attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Maximum number of reconnection attempts reached');
      this.clientId = null;
      return;
    }
    
    // Clear any existing reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    
    // Calculate backoff time with exponential increase and some randomness
    const backoff = Math.min(30000, this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts)) 
                  + Math.floor(Math.random() * 1000);
    
    this.reconnectAttempts++;
    console.log(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${backoff}ms`);
    
    this.reconnectTimer = setTimeout(() => {
      console.log('Attempting to reconnect...');
      this.connect().catch(error => {
        console.error('Error during reconnection attempt:', error);
      });
    }, backoff);
  }
  
  /**
   * Start sending periodic pings to keep the connection alive
   * @private
   */
  _startPingInterval() {
    this._stopPingInterval(); // Clear any existing interval
    
    this.pingInterval = setInterval(() => {
      if (this.isConnected) {
        try {
          this.socket.send(JSON.stringify({ type: 'ping' }));
          console.debug('Ping sent to server');
        } catch (error) {
          console.error('Error sending ping:', error);
          this._stopPingInterval();
        }
      }
    }, 25000); // Send ping every 25 seconds
  }
  
  /**
   * Stop the ping interval
   * @private
   */
  _stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Sends a text message to the server
   * @param {string} text - The text to send
   */
  sendText(text) {
    if (!this.isConnected) {
      throw new Error('WebSocket not connected');
    }

    const message = {
      type: 'text',
      content: text
    };

    this.socket.send(JSON.stringify(message));
  }

  /**
   * Sends an audio message to the server (base64)
   * @param {string} audioBase64 - The audio encoded in base64
   */
  sendAudio(audioBase64) {
    if (!this.isConnected) {
      throw new Error('WebSocket not connected');
    }

    const message = {
      type: 'audio',
      content: audioBase64
    };

    this.socket.send(JSON.stringify(message));
  }

  /**
   * Adds a listener for a specific message type
   * @param {string} type - The message type (text_response, audio_response, error, connect, disconnect)
   * @param {Function} callback - The function to call when a message of this type arrives
   */
  addListener(type, callback) {
    if (this.listeners[type]) {
      this.listeners[type].push(callback);
    } else {
      console.warn(`Unsupported listener type: ${type}`);
    }
  }

  /**
   * Removes a listener
   * @param {string} type - The message type
   * @param {Function} callback - The function to remove
   */
  removeListener(type, callback) {
    if (this.listeners[type]) {
      this.listeners[type] = this.listeners[type].filter(cb => cb !== callback);
    }
  }

  /**
   * Closes the WebSocket connection
   */
  disconnect() {
    if (this.socket && this.isConnected) {
      this.socket.close();
    }
  }

  /**
   * Notifies all listeners of a specific type
   * @param {string} type - The message type
   * @param {Object} data - The data to pass to the listeners
   * @private
   */
  _notifyListeners(type, data) {
    if (this.listeners[type]) {
      this.listeners[type].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error executing listener for ${type}:`, error);
        }
      });
    }
  }

  /**
   * Returns the current client_id
   * @returns {string|null} - The client_id or null if not connected
   */
  getClientId() {
    return this.clientId;
  }
}