/**
 * Market Assistant WebSocket Client
 * Questo script gestisce la connessione WebSocket con il server Market Assistant
 * e l'elaborazione dei messaggi ricevuti.
 */
class MarketAssistantClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.socket = null;
    this.clientId = null;
    this.listeners = {
      text_response: [],
      audio_response: [],
      table_response: [],
      error: [],
      connect: [],
      disconnect: []
    };
    this.isConnected = false;
  }

  /**
   * Inizializza la connessione WebSocket
   */
  connect() {
    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(`${this.baseUrl}/ws`);

        this.socket.onopen = () => {
          console.log('WebSocket connesso');
          this.isConnected = true;
          this._notifyListeners('connect', { status: 'connected' });
        };

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('Messaggio ricevuto:', data);

            // Salva il client_id quando lo riceviamo dal server
            if (data.client_id && !this.clientId) {
              this.clientId = data.client_id;
              resolve(this.clientId);
            }

            // Notifica i listener in base al tipo di messaggio
            if (data.type) {
              this._notifyListeners(data.type, data);
            }
          } catch (error) {
            console.error('Errore nel parsing del messaggio:', error);
            this._notifyListeners('error', { 
              error: 'Errore nel parsing del messaggio', 
              details: error.message 
            });
          }
        };

        this.socket.onerror = (error) => {
          console.error('Errore WebSocket:', error);
          this._notifyListeners('error', { 
            error: 'Errore di connessione WebSocket', 
            details: error 
          });
          reject(error);
        };

        this.socket.onclose = () => {
          console.log('WebSocket disconnesso');
          this.isConnected = false;
          this.clientId = null;
          this._notifyListeners('disconnect', { status: 'disconnected' });
        };
      } catch (error) {
        console.error('Errore durante la creazione della connessione WebSocket:', error);
        reject(error);
      }
    });
  }

  /**
   * Invia un messaggio di testo al server
   * @param {string} text - Il testo da inviare
   */
  sendText(text) {
    if (!this.isConnected) {
      throw new Error('WebSocket non connesso');
    }

    const message = {
      type: 'text',
      content: text
    };

    this.socket.send(JSON.stringify(message));
  }

  /**
   * Invia un messaggio audio al server (base64)
   * @param {string} audioBase64 - L'audio codificato in base64
   */
  sendAudio(audioBase64) {
    if (!this.isConnected) {
      throw new Error('WebSocket non connesso');
    }

    const message = {
      type: 'audio',
      content: audioBase64
    };

    this.socket.send(JSON.stringify(message));
  }

  /**
   * Aggiunge un listener per un tipo specifico di messaggio
   * @param {string} type - Il tipo di messaggio (text_response, audio_response, error, connect, disconnect)
   * @param {Function} callback - La funzione da chiamare quando arriva un messaggio di questo tipo
   */
  addListener(type, callback) {
    if (this.listeners[type]) {
      this.listeners[type].push(callback);
    } else {
      console.warn(`Tipo di listener non supportato: ${type}`);
    }
  }

  /**
   * Rimuove un listener
   * @param {string} type - Il tipo di messaggio
   * @param {Function} callback - La funzione da rimuovere
   */
  removeListener(type, callback) {
    if (this.listeners[type]) {
      this.listeners[type] = this.listeners[type].filter(cb => cb !== callback);
    }
  }

  /**
   * Chiude la connessione WebSocket
   */
  disconnect() {
    if (this.socket && this.isConnected) {
      this.socket.close();
    }
  }

  /**
   * Notifica tutti i listener di un determinato tipo
   * @param {string} type - Il tipo di messaggio
   * @param {Object} data - I dati da passare ai listener
   * @private
   */
  _notifyListeners(type, data) {
    if (this.listeners[type]) {
      this.listeners[type].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Errore nell'esecuzione del listener per ${type}:`, error);
        }
      });
    }
  }

  /**
   * Restituisce il client_id corrente
   * @returns {string|null} - Il client_id o null se non connesso
   */
  getClientId() {
    return this.clientId;
  }
}

// Esempio di utilizzo:
// const client = new MarketAssistantClient('ws://localhost:8101');

// // Aggiungi listener per i diversi tipi di messaggi
// client.addListener('text_response', (data) => {
//   console.log('Risposta testuale ricevuta:', data.content);
//   // Aggiorna l'interfaccia utente con la risposta
//   document.getElementById('response').textContent = data.content;
// });

// client.addListener('audio_response', (data) => {
//   console.log('Risposta audio ricevuta:', data.content);
//   // Gestisci la risposta audio
//   document.getElementById('response').textContent = data.content;
// });

// client.addListener('error', (data) => {
//   console.error('Errore ricevuto:', data);
//   // Mostra l'errore all'utente
//   document.getElementById('error').textContent = data.content || data.error;
// });

// // Connetti al server
// client.connect()
//   .then(clientId => {
//     console.log('Connesso con ID:', clientId);
//     // Abilita l'interfaccia utente dopo la connessione
//     document.getElementById('sendButton').disabled = false;
//   })
//   .catch(error => {
//     console.error('Errore di connessione:', error);
//   });

// // Esempio di invio di un messaggio di testo
// document.getElementById('sendButton').addEventListener('click', () => {
//   const text = document.getElementById('input').value;
//   if (text) {
//     client.sendText(text);
//     document.getElementById('input').value = '';
//   }
// });