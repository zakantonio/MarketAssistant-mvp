// Configurazione API
const API_BASE_URL = getWebUrl(); // Use the same origin as the dashboard

// Dati globali
let statsData = null;
let allLogs = [];
// Store chart instances so we can destroy them before creating new ones
let charts = {
    searchTypeChart: null,
    dailySearchesChart: null
};

// Funzione per caricare le statistiche aggregate
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/logs/stats`);
        if (!response.ok) {
            throw new Error('Errore nel caricamento delle statistiche');
        }
        
        statsData = await response.json();
        
        // Aggiorna i componenti della dashboard che usano statistiche aggregate
        updateGeneralStats();
        updateSearchTypeChart();
        updateDailySearchesChart();
        updateTopProductsTable();
        updateNotFoundProductsTable();
        
        // Carica anche i log dettagliati per altre visualizzazioni
        await loadLogs();
    } catch (error) {
        console.error('Errore:', error);
        alert('Errore nel caricamento dei dati. Controlla la console per dettagli.');
    }
}

// Funzione per caricare tutti i log
async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/logs/?limit=1000`);
        if (!response.ok) {
            throw new Error('Errore nel caricamento dei log');
        }
        
        allLogs = await response.json();
        
        // Aggiorna i componenti che richiedono dati dettagliati
        updateSearchTypeTermTable();
    } catch (error) {
        console.error('Errore:', error);
        alert('Errore nel caricamento dei dati. Controlla la console per dettagli.');
    }
}

// Aggiorna le statistiche generali
function updateGeneralStats() {
    document.getElementById('total-searches').textContent = statsData.total_searches;
    document.getElementById('successful-searches').textContent = statsData.successful_searches;
    document.getElementById('failed-searches').textContent = statsData.failed_searches;
}

// Aggiorna il grafico dei tipi di ricerca
function updateSearchTypeChart() {
    // Prepara i dati per il grafico
    const labels = Object.keys(statsData.search_types);
    const data = Object.values(statsData.search_types);
    
    const ctx = document.getElementById('search-type-chart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.searchTypeChart) {
        charts.searchTypeChart.destroy();
    }
    
    // Create new chart and store the instance
    charts.searchTypeChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels.map(formatSearchType),
            datasets: [{
                data: data,
                backgroundColor: [
                    '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
                    '#5a5c69', '#858796', '#6f42c1', '#20c9a6', '#fd7e14'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

// Aggiorna il grafico dell'andamento giornaliero
function updateDailySearchesChart() {
    // Ordina le date
    const sortedDates = Object.keys(statsData.daily_stats).sort();
    
    // Prepara i dati per il grafico
    const totalData = sortedDates.map(date => statsData.daily_stats[date].total);
    const successData = sortedDates.map(date => statsData.daily_stats[date].success);
    const failedData = sortedDates.map(date => statsData.daily_stats[date].failed);
    
    const ctx = document.getElementById('daily-searches-chart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (charts.dailySearchesChart) {
        charts.dailySearchesChart.destroy();
    }
    
    // Create new chart and store the instance
    charts.dailySearchesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: sortedDates,
            datasets: [
                {
                    label: 'Totale Ricerche',
                    data: totalData,
                    borderColor: '#4e73df',
                    backgroundColor: 'rgba(78, 115, 223, 0.1)',
                    borderWidth: 2,
                    fill: true
                },
                {
                    label: 'Ricerche con Risultati',
                    data: successData,
                    borderColor: '#1cc88a',
                    backgroundColor: 'rgba(28, 200, 138, 0.1)',
                    borderWidth: 2,
                    fill: true
                },
                {
                    label: 'Ricerche Senza Risultati',
                    data: failedData,
                    borderColor: '#e74a3b',
                    backgroundColor: 'rgba(231, 74, 59, 0.1)',
                    borderWidth: 2,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

// Aggiorna la tabella dei prodotti più ricercati
function updateTopProductsTable() {
    // Aggiorna la tabella
    const tableBody = document.getElementById('top-products-table').querySelector('tbody');
    tableBody.innerHTML = '';
    
    statsData.top_products.forEach(product => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${product.term}</td>
            <td>${product.count}</td>
            <td>${product.found_percent.toFixed(1)}%</td>
        `;
        tableBody.appendChild(row);
    });
}

// Aggiorna la tabella dei prodotti non trovati
function updateNotFoundProductsTable() {
    // Aggiorna la tabella
    const tableBody = document.getElementById('not-found-products-table').querySelector('tbody');
    tableBody.innerHTML = '';
    
    statsData.top_not_found.forEach(product => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${product.term}</td>
            <td>${product.count}</td>
        `;
        tableBody.appendChild(row);
    });
}

// Aggiorna la tabella delle ricerche raggruppate per tipo e termine
function updateSearchTypeTermTable() {
    // Raggruppa per tipo di ricerca e termine
    const groupedSearches = {};
    
    allLogs.forEach(log => {
        if (log.query_term === 'all' || log.query_term === 'advanced_search') {
            return; // Ignora ricerche generiche
        }
        
        const key = `${log.search_type}|${log.query_term}`;
        
        if (!groupedSearches[key]) {
            groupedSearches[key] = { 
                search_type: log.search_type, 
                query_term: log.query_term, 
                total: 0, 
                found: 0 
            };
        }
        
        groupedSearches[key].total++;
        if (log.found) {
            groupedSearches[key].found++;
        }
    });
    
    // Converti in array e ordina per conteggio
    const sortedGroups = Object.values(groupedSearches)
        .sort((a, b) => b.total - a.total)
        .slice(0, 20); // Limita a 20 righe
    
    // Aggiorna la tabella
    const tableBody = document.getElementById('search-type-term-table').querySelector('tbody');
    tableBody.innerHTML = '';
    
    sortedGroups.forEach(group => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatSearchType(group.search_type)}</td>
            <td>${group.query_term}</td>
            <td>${group.total}</td>
            <td>${((group.found / group.total) * 100).toFixed(1)}%</td>
        `;
        tableBody.appendChild(row);
    });
}

// Formatta il tipo di ricerca per la visualizzazione
function formatSearchType(searchType) {
    switch(searchType) {
        case 'product':
            return 'Prodotto (Base)';
        case 'product_advanced':
            return 'Prodotto (Avanzata)';
        case 'recipe':
            return 'Ricetta (Base)';
        case 'recipe_advanced':
            return 'Ricetta (Avanzata)';
        default:
            return searchType;
    }
}

// Funzione per aggiornare automaticamente i dati
function setupAutoRefresh() {
    // Aggiorna i dati ogni 30 secondi
    // setInterval(loadStats, 60000);
    
    // Aggiungi un indicatore di ultimo aggiornamento
    const lastUpdatedElement = document.createElement('div');
    lastUpdatedElement.className = 'text-muted text-end mt-2';
    lastUpdatedElement.id = 'last-updated';
    document.querySelector('.container-fluid').appendChild(lastUpdatedElement);
    
    // Funzione per aggiornare il timestamp
    function updateTimestamp() {
        const now = new Date();
        document.getElementById('last-updated').textContent = 
            `Ultimo aggiornamento: ${now.toLocaleDateString()} ${now.toLocaleTimeString()}`;
    }
    
    // Aggiorna il timestamp quando i dati vengono caricati
    const originalLoadStats = loadStats;
    loadStats = async function() {
        await originalLoadStats();
        updateTimestamp();
    };
}

// Inizializza la dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    setupAutoRefresh();
    
    // Aggiungi pulsante per aggiornamento manuale
    const refreshButton = document.createElement('button');
    refreshButton.className = 'btn btn-primary mt-3 mb-3';
    refreshButton.textContent = 'Aggiorna Dati';
    refreshButton.addEventListener('click', loadStats);
    
    // Inserisci il pulsante all'inizio del container
    const container = document.querySelector('.container-fluid');
    container.insertBefore(refreshButton, container.firstChild.nextSibling);
});