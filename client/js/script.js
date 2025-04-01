const client = new MarketAssistantClient(getWebSocketUrl());
const chatContainer = document.getElementById('chatContainer');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const recordButton = document.getElementById('recordButton');
const microphoneIcon = document.getElementById('microphone');
const statusElement = document.getElementById('status');
const instructionText = document.getElementById('instruction');


function addMessage(text, type) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message');
    messageElement.classList.add(`${type}-message`);
    messageElement.textContent = text;
    chatContainer.appendChild(messageElement);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

let audioContext;
let analyser;
let dataArray;
let animationFrame;
let isRecording = false;

function getUniqueAisles(products) {
    const aisles = new Set(); 

    products.forEach(product => {
        if (product.location && product.location.aisle) {
            aisles.add(product.location.aisle);
        }
    });

    return Array.from(aisles); // Convert Set to array
}

function showHideImages(uniqueAisles) {
    const images = document.querySelectorAll('#aisles img');
    images.forEach(image => {
        const aisleId = image.getAttribute('data-id');
        if (uniqueAisles.includes(aisleId)) {
            image.style.display = 'block'; // Show image
        } else {
            image.style.display = 'none'; // Hide image
        }
    });
}

// Title
function displayRecipeInfo(recipe) {
    const title = document.getElementById('title');
    const description = document.getElementById('description');
    if (recipe) {
        title.innerHTML = recipe.name;
        description.innerHTML = recipe.description;
    } else {
        title.innerHTML = '';
        description.innerHTML = ''; 
    }
}

// Function to display product table
function displayProductTable(products) {
    const tableContainer = document.getElementById('productTableContainer');
    const tableBody = document.getElementById('productTableBody');

    const uniqueAisles = getUniqueAisles(products);
    showHideImages(uniqueAisles);

    // Clear existing table
    tableBody.innerHTML = '';

    const row = document.createElement('tr');

    // Name column
    const nameCell = document.createElement('td');
    nameCell.textContent = "PRODOTTO";
    row.appendChild(nameCell);

    // Location column
    const locationCell = document.createElement('td');
    locationCell.innerHTML = `REPARTO`;
    row.appendChild(locationCell);

    const aisleCell = document.createElement('td');
    aisleCell.innerHTML = `CORSIA`;
    row.appendChild(aisleCell);

    const shelfCell = document.createElement('td');
    shelfCell.innerHTML = `SCAFFALE`;
    row.appendChild(shelfCell);

    tableBody.appendChild(row);

    // Add a row for each product
    products.forEach(product => {
        const row = document.createElement('tr');

        // Name column
        const nameCell = document.createElement('td');
        nameCell.textContent = product.name;
        row.appendChild(nameCell);

        const location = product.location;

        // Location column
        const locationCell = document.createElement('td');
        locationCell.innerHTML = `
             ${location.section || 'N/A'}<br>
         `;
        row.appendChild(locationCell);

        const aisleCell = document.createElement('td');
        aisleCell.innerHTML = `
             ${location.aisle || 'N/A'}<br>
         `;
        row.appendChild(aisleCell);

        const shelfCell = document.createElement('td');
        shelfCell.innerHTML = `
             ${location.shelf || 'N/A'}
         `;
        row.appendChild(shelfCell);

        tableBody.appendChild(row);
    });

    // Show table
    tableContainer.style.display = 'block';

    // Scroll to table
    tableContainer.scrollIntoView({ behavior: 'smooth' });
}

// Function to show/hide product details
function toggleDetails(element) {
    const detailsDiv = element.nextElementSibling;
    if (detailsDiv.style.display === 'block') {
        detailsDiv.style.display = 'none';
        element.textContent = 'Mostra dettagli';
    } else {
        detailsDiv.style.display = 'block';
        element.textContent = 'Nascondi dettagli';
    }
}

// Listener per i messaggi
client.addListener('event_response', (data) => {

    console.log(data.content);
    if (data.content === 'processing') {
        setIsDoingOperation(true, "BE is processing");
        microphoneIcon.style.display = 'block';
        processingRecordButton();
    } else if (data.content === 'replying') {
        setIsDoingOperation(false, "BE stop processing");
        showPage("page-03");
        stopAnimation();
    } else if (data.content === 'errornotfound') {
        setIsDoingOperation(false, "BE error processing");
        showErrorText();
        stopAnimation();
        microphoneIcon.style.display = 'block';
    }
});

client.addListener('text_response', (data) => {
    addMessage(data.content, 'assistant');
});

client.addListener('table_response', (data) => {
    // Verifica se ci sono risultati di prodotti da visualizzare
    if (data.content && data.content.products && data.content.products.length > 0) {
        displayRecipeInfo(data.content.recipe);
        displayProductTable(data.content.products);
    } else {
        // Nascondi la tabella se non ci sono risultati
        document.getElementById('productTableContainer').style.display = 'none';
    }
});

client.addListener('audio_response', (data) => {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', 'assistant-message');

    // Create text content
    const textSpan = document.createElement('span');
    textSpan.textContent = data.content;

    // Create play button
    const playButton = document.createElement('button');
    playButton.innerHTML = '🔊';
    playButton.style.marginLeft = '10px';
    playButton.onclick = () => {
        const audio = new Audio('data:audio/wav;base64,' + data.audio);
        audio.play();
    };

    // Append elements
    messageDiv.appendChild(textSpan);
    messageDiv.appendChild(playButton);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
});
client.addListener('error', (data) => {
    addMessage(data.content || data.error || 'Errore sconosciuto', 'error');
});

client.addListener('connect', () => {
    statusElement.textContent = 'Connesso';
    messageInput.disabled = false;
    sendButton.disabled = false;
    recordButton.disabled = false;
});

client.addListener('disconnect', () => {
    statusElement.textContent = 'Disconnesso';
    messageInput.disabled = true;
    sendButton.disabled = true;
    recordButton.disabled = true;
});

// Text error
function showErrorText() {
    const errorElement = document.getElementById('errorText');
    if (errorElement) {
        errorElement.style.display = 'block';
        errorElement.textContent = 'Non sono riuscito a trovare il prodotto.\nRiprova tenendo premuto il tasto.';
    }
}

function hideErrorText() {
    const errorElement = document.getElementById('errorText');
    if (errorElement) {
        errorElement.style.display = 'none';
    }
}

client.connect()
    .then(clientId => {
        statusElement.textContent = `Connesso (ID: ${clientId})`;
    })
    .catch(error => {
        statusElement.textContent = `Errore di connessione: ${error.message}`;
        addMessage(`Errore di connessione: ${error.message}`, 'error');
    });

    
sendButton.addEventListener('click', () => {
    const text = messageInput.value.trim();
    if (text) {
        addMessage(text, 'user');
        client.sendText(text);
        messageInput.value = '';
    }
});

messageInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        sendButton.click();
    }
});

let mediaRecorder;
let audioChunks = [];

async function onRecorderStart() {

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(stream);
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        dataArray = new Uint8Array(analyser.frequencyBinCount);

        const highPassFilter = audioContext.createBiquadFilter();
        highPassFilter.type = "highpass";
        highPassFilter.frequency.value = 2000;

        source.connect(highPassFilter);
        highPassFilter.connect(analyser);

        animateRecordButton();
        hideErrorText();
        instructionText.style.display = 'none';
        playAudio(startRecordingSound);

        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.addEventListener('dataavailable', (event) => {
            audioChunks.push(event.data);
        });

        mediaRecorder.start();
        isRecording = true;
        // recordButton.textContent = '🔴';
    } catch (error) {
        console.error('Errore accesso al microfono:', error);
        addMessage(`Errore accesso al microfono: ${error.message}`, 'error');
    }
}

// Pulse animation recordButton
function animateRecordButton() {
    function step() {
        analyser.getByteFrequencyData(dataArray);
        const volume = dataArray.reduce((a, b) => a + b) / dataArray.length;
        const scale = 1 + (volume / 256) * 0.5; // Scala tra 1 e 1.5
        recordButton.style.transform = `scale(${scale})`;
        animationFrame = requestAnimationFrame(step);
    }
    step();
}
let isAnimating = false; 

// Rotate animation recordButton
function processingRecordButton() {
    let angle = 0;
    let time = 0;
    const div = document.getElementById("recordButton");

    isAnimating = true;

    function easeInOutQuad(t) {
        return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    }

    function rotate() {
        if (isAnimating === false) return; // Se isAnimating è false, interrompi l'animazione

        let progress = (time % 1);
        let speedFactor = easeInOutQuad(progress);
        let speed = speedFactor * 5;

        angle = ((angle + speed) % 360);
        div.style.transform = `rotate(${angle}deg)`;

        time += 0.01;

        requestAnimationFrame(rotate); 
    }

    rotate(); 

}

function stopAnimation() {
    isAnimating = false;
    const div = document.getElementById("recordButton");
    div.style.transform = `rotate(0deg)`;
}

window.stopAnimation = stopAnimation

let debounceTimeoutMouse;
let debounceTimeoutTouch;

recordButton.addEventListener('mousedown', async () => {
onRecordButtonClick();
});

recordButton.addEventListener('touchstart', async () => {
    onRecordButtonClick();
});

function onRecordButtonClick() {
    clearTimeout(debounceTimeoutTouch);

    debounceTimeoutTouch = setTimeout(async () => {
        await onRecorderStart();
    }, 300); // 300ms di debounce
}

function onRecorderStop() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        isRecording =false;
        // recordButton.textContent = '🎤';
        // recordButton.textContent = ' ';
        cancelAnimationFrame(animationFrame);
        recordButton.style.transform = 'scale(1)';
        microphoneIcon.style.display = 'block';
        playAudio(stopRecordingSound);

        mediaRecorder.addEventListener('stop', async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const reader = new FileReader();

            reader.onloadend = () => {
                const base64Audio = reader.result.split(',')[1];
                addMessage('Messaggio vocale inviato', 'user');
                client.sendAudio(base64Audio);
            };

            reader.readAsDataURL(audioBlob);

            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        });
    }
}

recordButton.addEventListener('mouseup', () => {
    clearTimeout(debounceTimeoutMouse);

    onRecorderStop();
});

recordButton.addEventListener('touchend', () => {
    clearTimeout(debounceTimeoutTouch)

    onRecorderStop();
});

window.addEventListener('beforeunload', () => {
    client.disconnect();
});

const data = [
    // { "id": "1", "name": "Banana Bread", "prompt": "Dove trovo gli ingredienti per preparare la ricetta della Banana Bread", "image": "assets//recipes//banana-bread.webp" },
    { "id": "2", "name": "Milkshake", "prompt": "Dove trovo gli ingredienti per preparare la ricetta del Milkshake?", "image": "assets//recipes//milkshake.jpg" },
    { "id": "3", "name": "Pancake", "prompt": "Dove trovo gli ingredienti per preparare la ricetta dei Pancakes?", "image": "assets//recipes//pancakes.jpg" },
    { "id": "4", "name": "Biscotti", "prompt": "Dove trovo gli ingredienti per preparare la ricetta dei Biscotti?", "image": "assets//recipes//chocolate-bisquits.jpg" },
    { "id": "5", "name": "Carbonara", "prompt": "Dove trovo gli ingredienti per preparare la ricetta della Carbonara?", "image": "assets//recipes//carbonara.webp" },
    { "id": "6", "name": "Lasagne", "prompt": "Dove trovo gli ingredienti per preparare la ricetta delle Lasagne?", "image": "assets//recipes//lasagne.jpg" },
    { "id": "7", "name": "Tiramisù", "prompt": "Dove trovo gli ingredienti per preparare la ricetta del Tiramisù?", "image": "assets//recipes//tiramisù.jpeg" },
    { "id": "8", "name": "Cous cous", "prompt": "Dove trovo gli ingredienti per preparare la ricetta del  Cous Cous?", "image": "assets//recipes//cous-cous.webp" },
    { "id": "9", "name": "Pizza", "prompt": "Dove trovo gli ingredienti per preparare la ricetta della Pizza?", "image": "assets//recipes//pizza.jpg" },
    { "id": "10", "name": "Risotto", "prompt": "Dove trovo gli ingredienti per preparare la ricetta del Risotto?", "image": "assets//recipes//risotto.webp" }
];

function populateScroll(showImage = true) {
    document.getElementById("scrollContainer").hidden = false;
    document.getElementById("scrollContainerSmall").hidden = false;

    let container = null;
    let className = null;
    if (showImage === true) {
        container = document.getElementById("scrollContainer");
        className = "card";
    } else {
        container = document.getElementById("scrollContainerSmall");
        className = "cardSmall";
    }

    container.innerHTML = "";
    data.forEach(item => {
        const card = document.createElement("div");
        card.classList.add(className);
        // Add data-id attribute to the card
        card.setAttribute('data-id', item.id);

        if (showImage === true) {
            const img = document.createElement("img");
            img.src = item.image;
            img.alt = item.name;
            card.appendChild(img);
        }

        const title = document.createElement("p");
        title.textContent = item.name;

        card.appendChild(title);
        container.appendChild(card);

        card.addEventListener("click", () => {
            handleCardClick(item.id);
        });
    });
}

function handleCardClick(id) {
    showPage("page-02");
    instructionText.style.display = 'none';
    
    const selectedItem = data.find(item => item.id === id);
    if (selectedItem) {
        client.sendText(selectedItem.prompt);
    } else {
        console.warn(`No recipe found for id: ${id}`);
    }
    
    hideErrorText();
}
function hideScroll() {
    document.getElementById("scrollContainer").hidden = true;
    document.getElementById("scrollContainerSmall").hidden = true;
}
