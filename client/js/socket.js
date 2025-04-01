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
      event_response: [],
      table_response: [],
      error: [],
      connect: [],
      disconnect: []
    };
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectInterval = 3000; // Start with 3 seconds
    this.reconnectTimer = null;
  }

  /**
   * Initializes the WebSocket connection
   */
  connect() {
    return new Promise((resolve, reject) => {
      try {
        console.log(`Connection attempt to ${this.baseUrl}/ws`);
        this.socket = new WebSocket(`${this.baseUrl}/ws`);
        
        // Update connection status
        this._updateConnectionStatus('Connecting...');
        
        // Set a connection timeout
        const connectionTimeout = setTimeout(() => {
          if (!this.isConnected) {
            console.error('WebSocket connection timeout');
            this.socket.close();
            this._updateConnectionStatus('Disconnected');
            reject(new Error('WebSocket connection timeout'));
          }
        }, 10000); // 10 seconds timeout
        
        this.socket.onopen = () => {
          clearTimeout(connectionTimeout);
          console.log('WebSocket successfully connected');
          this.isConnected = true;
          this.reconnectAttempts = 0; // Reset reconnect attempts on successful connection
          this._updateConnectionStatus('Connected');
          this._notifyListeners('connect', { status: 'connected' });
          resolve(this.clientId);
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
          this._updateConnectionStatus('Disconnected');
          this._notifyListeners('disconnect', { 
            status: 'disconnected', 
            code: event.code, 
            reason: event.reason 
          });
          
          // Attempt to reconnect if not a normal closure
          if (event.code !== 1000 && event.code !== 1001) {
            this._attemptReconnect();
          } else {
            this.clientId = null; // Only clear client ID on normal closure
          }
        };
      } catch (error) {
        console.error('Error creating WebSocket connection:', error);
        this._updateConnectionStatus('Error');
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
      this._updateConnectionStatus('Reconnection failed');
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
    this._updateConnectionStatus(`Reconnecting in ${Math.round(backoff/1000)}s...`);
    
    console.log(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${backoff}ms`);
    
    this.reconnectTimer = setTimeout(() => {
      console.log('Attempting to reconnect...');
      this.connect().catch(error => {
        console.error('Error during reconnection attempt:', error);
      });
    }, backoff);
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

  /**
   * Updates the connection status in the UI
   * @param {string} text - The connection status text
   * @private
   */
  _updateConnectionStatus(text) {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
      statusElement.textContent = text;
      
      // Remove all status classes
      statusElement.classList.remove('connected', 'disconnected');
      
      // Add appropriate class based on status
      if (text === 'Connected') {
        statusElement.classList.add('connected');
      } else if (text === 'Disconnected' || text === 'Error') {
        statusElement.classList.add('disconnected');
      }
    }
  }
}

