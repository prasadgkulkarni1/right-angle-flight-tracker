const resultsContainer = document.getElementById('resultsContainer');
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');
const providerSelect = document.getElementById('providerSelect');
const providerStatus = document.getElementById('providerStatus');

let currentSearchId = null;
let isSearching = false;
let availableProviders = [];

// Register service worker for PWA support
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => console.log('Service worker registered:', reg.scope))
            .catch(err => console.warn('Service worker registration failed:', err));
    });
}

// Load available providers on page load
async function loadProviders() {
    try {
        const response = await fetch('/api/providers');
        const data = await response.json();
        availableProviders = data.providers;

        // Clear and populate dropdown
        providerSelect.innerHTML = '';

        // Add providers to dropdown
        availableProviders.forEach(provider => {
            const option = document.createElement('option');
            option.value = provider.provider_id;
            option.textContent = provider.name;

            // Disable if not configured
            if (!provider.configured) {
                option.textContent += ' (Not configured)';
                option.disabled = true;
            }

            providerSelect.appendChild(option);
        });

        // Select first available provider
        const firstAvailable = availableProviders.find(p => p.configured);
        if (firstAvailable) {
            providerSelect.value = firstAvailable.provider_id;
            updateProviderStatus(firstAvailable);
        }

        // Add change listener
        providerSelect.addEventListener('change', onProviderChange);

    } catch (error) {
        console.error('Error loading providers:', error);
        providerSelect.innerHTML = '<option value="mock">Mock Provider (Fallback)</option>';
    }
}

function onProviderChange() {
    const selectedProviderId = providerSelect.value;
    const provider = availableProviders.find(p => p.provider_id === selectedProviderId);
    if (provider) {
        updateProviderStatus(provider);
    }
}

function updateProviderStatus(provider) {
    if (provider.configured) {
        providerStatus.textContent = '✓ Ready';
        providerStatus.className = 'provider-status status-ready';
    } else {
        providerStatus.textContent = `✗ ${provider.missing_vars.join(', ')} required`;
        providerStatus.className = 'provider-status status-error';
    }
}

// Initialize providers on page load
loadProviders();

// Auto-resize textarea
queryInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// Handle send
sendBtn.addEventListener('click', sendQuery);
queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendQuery();
    }
});

function fillExample(text) {
    queryInput.value = text;
    queryInput.focus();
}

async function sendQuery() {
    const query = queryInput.value.trim();
    if (!query || isSearching) return;
    
    // Clear previous results
    resultsContainer.innerHTML = '';
    
    // Disable input and show loading
    isSearching = true;
    sendBtn.disabled = true;
    const originalText = sendBtn.innerHTML;
    sendBtn.innerHTML = `
        <div class="loading">
            <span>Searching...</span>
            <div class="loading-dots">
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
            </div>
        </div>
    `;
    
    try {
        // Send search request with selected provider
        const provider = providerSelect.value;
        if (!provider) {
            showError('Please select a flight data provider');
            resetSearchButton();
            return;
        }

        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query, provider })
        });
        
        const data = await response.json();
        currentSearchId = data.search_id;
        
        // Poll for status
        pollStatus();
    } catch (error) {
        showError(`Error: ${error.message}`);
        sendBtn.innerHTML = originalText;
        isSearching = false;
        sendBtn.disabled = false;
    }
}

async function pollStatus() {
    if (!currentSearchId) return;

    try {
        const response = await fetch(`/api/status/${currentSearchId}`);
        const data = await response.json();

        // Check status
        if (data.status === 'complete') {
            if (data.results && data.results.length > 0) {
                displayFlightCards(data.results);
            } else {
                showError('No flights found for your search criteria');
            }
            resetSearchButton();
            currentSearchId = null;
        } else if (data.status === 'error') {
            const errorMsg = data.messages && data.messages.length > 0
                ? data.messages[data.messages.length - 1].content
                : 'An error occurred';
            showError(errorMsg);
            resetSearchButton();
            currentSearchId = null;
        } else {
            // Continue polling
            setTimeout(pollStatus, 500);
        }
    } catch (error) {
        console.error('Polling error:', error);
        showError(`Error: ${error.message}`);
        resetSearchButton();
    }
}

function resetSearchButton() {
    isSearching = false;
    sendBtn.disabled = false;
    sendBtn.innerHTML = '<span>Search Flights</span>';
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message error';
    errorDiv.innerHTML = `<div class="message-content">${message}</div>`;
    resultsContainer.appendChild(errorDiv);
}

// Store current flights for sorting
let currentFlights = [];

function displayFlightCards(flights) {
    // Store flights for sorting
    currentFlights = flights;

    // Clear previous results
    resultsContainer.innerHTML = '';

    // Add results header
    const header = document.createElement('div');
    header.className = 'results-header';
    header.innerHTML = `
        <h3 class="results-count">Found ${flights.length} flight${flights.length > 1 ? 's' : ''}</h3>
        <div class="sort-controls">
            <button onclick="sortFlights('price')" class="sort-btn active" id="sortByPrice">
                Price (Low to High)
            </button>
            ${flights.some(f => f.duration) ? `
                <button onclick="sortFlights('duration')" class="sort-btn" id="sortByDuration">
                    Duration
                </button>
            ` : ''}
        </div>
    `;
    resultsContainer.appendChild(header);

    // Display each flight card
    flights.forEach((flight, index) => {
        displayFlightCard(flight, index);
    });

    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function sortFlights(criteria) {
    // Update active button
    document.querySelectorAll('.sort-btn').forEach(btn => btn.classList.remove('active'));

    if (criteria === 'price') {
        currentFlights.sort((a, b) => a.price - b.price);
        document.getElementById('sortByPrice')?.classList.add('active');
    } else if (criteria === 'duration') {
        currentFlights.sort((a, b) => {
            const durationA = parseDuration(a.duration);
            const durationB = parseDuration(b.duration);
            return durationA - durationB;
        });
        document.getElementById('sortByDuration')?.classList.add('active');
    }

    displayFlightCards(currentFlights);
}

function parseDuration(duration) {
    if (!duration) return 0;

    // Handle ISO 8601 duration format (e.g., "PT13H30M")
    if (duration.startsWith('PT')) {
        const hours = duration.match(/(\d+)H/);
        const minutes = duration.match(/(\d+)M/);
        return (hours ? parseInt(hours[1]) : 0) * 60 + (minutes ? parseInt(minutes[1]) : 0);
    }

    // Handle simple format (e.g., "13h 30m")
    const hours = duration.match(/(\d+)h/);
    const minutes = duration.match(/(\d+)m/);
    return (hours ? parseInt(hours[1]) : 0) * 60 + (minutes ? parseInt(minutes[1]) : 0);
}

function formatDuration(duration) {
    if (!duration) return 'N/A';

    // Handle ISO 8601 duration format (e.g., "PT13H30M")
    if (duration.startsWith('PT')) {
        const hours = duration.match(/(\d+)H/);
        const minutes = duration.match(/(\d+)M/);
        const h = hours ? parseInt(hours[1]) : 0;
        const m = minutes ? parseInt(minutes[1]) : 0;
        return m > 0 ? `${h}h ${m}m` : `${h}h`;
    }

    // Already in simple format
    return duration;
}

function displayFlightCard(flight, index = 0) {
    const card = document.createElement('div');
    card.className = 'flight-card';

    // Build price display with conversion info if available
    let priceHTML = `<div class="flight-price">${flight.currency} ${flight.price}</div>`;
    if (flight.original_currency && flight.original_currency !== flight.currency) {
        priceHTML += `<div class="price-subtitle">Converted from ${flight.original_currency} ${flight.original_price}</div>`;
    } else {
        priceHTML += `<div class="price-subtitle">Total price for ${flight.trip_type}</div>`;
    }

    // Add "Best Deal" badge for the cheapest flight (first in sorted list)
    const bestDealBadge = index === 0 ? '<span class="badge badge-best">Best Deal</span>' : '';

    // Format stops display
    const stopsText = flight.stops !== undefined
        ? (flight.stops === 0 ? 'Direct' : `${flight.stops} stop${flight.stops > 1 ? 's' : ''}`)
        : '';

    card.innerHTML = `
        <div class="flight-header">
            <div class="flight-price-section">
                ${priceHTML}
            </div>
            <div class="flight-badges">
                ${bestDealBadge}
                <span class="badge badge-type">${flight.trip_type}</span>
            </div>
        </div>
        <div class="flight-details">
            <div class="detail-item">
                <div class="detail-label">Airline</div>
                <div class="detail-value airline-info">
                    <span class="airline-code">${flight.airline}</span>
                    <span>${flight.flight_number}</span>
                </div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Departure</div>
                <div class="detail-value">${formatDate(flight.departure_date)}</div>
            </div>
            ${flight.return_date ? `
                <div class="detail-item">
                    <div class="detail-label">Return</div>
                    <div class="detail-value">${formatDate(flight.return_date)}</div>
                </div>
            ` : ''}
            ${flight.duration ? `
                <div class="detail-item">
                    <div class="detail-label">Duration</div>
                    <div class="detail-value">${formatDuration(flight.duration)}</div>
                </div>
            ` : ''}
            ${stopsText ? `
                <div class="detail-item">
                    <div class="detail-label">Stops</div>
                    <div class="detail-value">${stopsText}</div>
                </div>
            ` : ''}
        </div>
        <button class="book-btn" onclick="window.open('${flight.booking_url}', '_blank')">
            Book Flight
        </button>
    `;

    resultsContainer.appendChild(card);
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
        weekday: 'short', 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}
