const getWebUrl = () => {
    
    if (window.ENV) {
        console.log('Using environment variables:', window.ENV);
        
        const protocol = window.location.protocol;
        const hostname = window.ENV.HOST;
        const port = window.ENV.PORT;

        console.log('connecting to:',`${protocol}//${hostname}:${port}`);
        
        return `${protocol}//${hostname}:${port}`;
    }
    
    const protocol = window.location.protocol;
    return `${protocol}//${window.location.hostname}:8101`;
};

const getWebSocketUrl = () => {
    
    if (window.ENV) {
        console.log('Using environment variables:', window.ENV);
       
        const protocol = window.ENV.WS_PROTOCOL || (window.location.protocol === 'https:' ? 'wss:' : 'ws:');
        const hostname = window.ENV.HOST || window.location.hostname;
        const port = window.ENV.PORT || '8101';

        console.log('connecting to:',`${protocol}//${hostname}:${port}`);
        
        return `${protocol}//${hostname}:${port}`;
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.hostname}:8101`;
};

// Date
function updateDate() {
    const now = new Date();
    const day = now.getDate().toString().padStart(2, '0');
    const months = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
    ];
    const month = months[now.getMonth()];

    document.querySelectorAll('#date').forEach(element => {
        element.textContent = `${day} ${month}`;
    });
}

updateDate();
setInterval(updateDate, 86400000);

// Clock
function updateClock() {
    const now = new Date();
    const hours = now.getHours().toString().padStart(2, '0');
    const minutes = now.getMinutes().toString().padStart(2, '0');

    document.querySelectorAll('#clock').forEach(element => {
        element.textContent = `${hours}.${minutes}`;
    });
}

updateClock();
setInterval(updateClock, 1000);

document.addEventListener('DOMContentLoaded', () => {
    // Disable menu
    document.addEventListener('contextmenu', (event) => {
        event.preventDefault();
    });

    // Disable double click
    document.addEventListener('dblclick', (event) => {
        event.preventDefault();
    });

    // Disable double tap
    let touchCount = 0;
    let lastTouchTime = 0;

    document.addEventListener('touchend', (event) => {
        const currentTime = new Date().getTime();
        touchCount++;

        if (touchCount === 2 && currentTime - lastTouchTime < 500) {
            event.preventDefault();
            touchCount = 0; // Reset counter
        } else {
            lastTouchTime = currentTime;
            if (touchCount > 2) {
                touchCount = 1; // Reset counter
            }
        }
    });

    // Disable select
    document.onselectstart = () => false;
    document.onmousedown = () => false;
});

// Sound effects
const startRecordingSound = 'assets/effects/start.wav';
const stopRecordingSound = 'assets/effects/end.wav';

function playAudio(url, volume = 0.2) {
    const audio = new Audio(url);
    audio.volume = volume;
    audio.addEventListener('error', (error) => {
        console.error('Errore durante la riproduzione dell\'audio:', error);
    });
    audio.play().catch((error) => {
        console.error('Errore durante la riproduzione dell\'audio:', error);
    });
}