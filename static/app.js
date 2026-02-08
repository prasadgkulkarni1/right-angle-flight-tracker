const resultsContainer = document.getElementById('resultsContainer');
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');
const providerSelect = document.getElementById('providerSelect');
const providerStatus = document.getElementById('providerStatus');

let currentSearchId = null;
let isSearching = false;
let availableProviders = [];
let currentFlights = [];

// Register service worker for PWA support
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.min.js').catch(() => {});
    });
}

// Shared duration parser: returns minutes from ISO 8601 or "Xh Ym" format
function parseDuration(d) {
    if (!d) return 0;
    const iso = d.startsWith('PT');
    const h = d.match(iso ? /(\d+)H/ : /(\d+)h/);
    const m = d.match(iso ? /(\d+)M/ : /(\d+)m/);
    return (h ? +h[1] : 0) * 60 + (m ? +m[1] : 0);
}

function formatDuration(d) {
    if (!d) return 'N/A';
    if (!d.startsWith('PT')) return d;
    const mins = parseDuration(d);
    const h = Math.floor(mins / 60), m = mins % 60;
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

const dateFormatter = new Intl.DateTimeFormat('en-US', {
    weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
});

function formatDate(dateStr) {
    return dateFormatter.format(new Date(dateStr));
}

function updateProviderStatus(provider) {
    providerStatus.textContent = provider.configured
        ? '✓ Ready'
        : `✗ ${provider.missing_vars.join(', ')} required`;
    providerStatus.className = `provider-status ${provider.configured ? 'status-ready' : 'status-error'}`;
}

async function loadProviders() {
    try {
        const { providers } = await (await fetch('/api/providers')).json();
        availableProviders = providers;
        providerSelect.innerHTML = '';

        providers.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.provider_id;
            opt.textContent = p.configured ? p.name : `${p.name} (Not configured)`;
            opt.disabled = !p.configured;
            providerSelect.appendChild(opt);
        });

        const first = providers.find(p => p.configured);
        if (first) {
            providerSelect.value = first.provider_id;
            updateProviderStatus(first);
        }

        providerSelect.addEventListener('change', () => {
            const p = availableProviders.find(p => p.provider_id === providerSelect.value);
            if (p) updateProviderStatus(p);
        });
    } catch (e) {
        providerSelect.innerHTML = '<option value="mock">Mock Provider (Fallback)</option>';
    }
}

loadProviders();

queryInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = this.scrollHeight + 'px';
});

sendBtn.addEventListener('click', sendQuery);
queryInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuery(); }
});

function fillExample(text) { queryInput.value = text; queryInput.focus(); }

function resetSearchButton() {
    isSearching = false;
    sendBtn.disabled = false;
    sendBtn.innerHTML = '<span>Search Flights</span>';
}

function showError(msg) {
    const el = document.createElement('div');
    el.className = 'message error';
    el.innerHTML = `<div class="message-content">${msg}</div>`;
    resultsContainer.appendChild(el);
}

async function sendQuery() {
    const query = queryInput.value.trim();
    if (!query || isSearching) return;

    resultsContainer.innerHTML = '';
    isSearching = true;
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<div class="loading"><span>Searching...</span><div class="loading-dots"><div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div></div></div>';

    try {
        const provider = providerSelect.value;
        if (!provider) { showError('Please select a flight data provider'); resetSearchButton(); return; }

        const res = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, provider })
        });
        currentSearchId = (await res.json()).search_id;
        pollStatus();
    } catch (err) {
        showError(`Error: ${err.message}`);
        resetSearchButton();
    }
}

async function pollStatus() {
    if (!currentSearchId) return;
    try {
        const data = await (await fetch(`/api/status/${currentSearchId}`)).json();

        if (data.status === 'complete') {
            data.results?.length > 0 ? displayFlightCards(data.results) : showError('No flights found for your search criteria');
            resetSearchButton();
            currentSearchId = null;
        } else if (data.status === 'error') {
            showError(data.messages?.length > 0 ? data.messages[data.messages.length - 1].content : 'An error occurred');
            resetSearchButton();
            currentSearchId = null;
        } else {
            setTimeout(pollStatus, 500);
        }
    } catch (err) {
        showError(`Error: ${err.message}`);
        resetSearchButton();
    }
}

function displayFlightCards(flights) {
    currentFlights = flights;
    resultsContainer.innerHTML = '';

    const frag = document.createDocumentFragment();

    const header = document.createElement('div');
    header.className = 'results-header';
    const hasDuration = flights.some(f => f.duration);
    header.innerHTML = `<h3 class="results-count">Found ${flights.length} flight${flights.length > 1 ? 's' : ''}</h3><div class="sort-controls"><button onclick="sortFlights('price')" class="sort-btn active" id="sortByPrice">Price (Low to High)</button>${hasDuration ? '<button onclick="sortFlights(\'duration\')" class="sort-btn" id="sortByDuration">Duration</button>' : ''}</div>`;
    frag.appendChild(header);

    flights.forEach((flight, i) => frag.appendChild(buildFlightCard(flight, i)));
    resultsContainer.appendChild(frag);
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function sortFlights(criteria) {
    document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
    if (criteria === 'price') {
        currentFlights.sort((a, b) => a.price - b.price);
        document.getElementById('sortByPrice')?.classList.add('active');
    } else if (criteria === 'duration') {
        currentFlights.sort((a, b) => parseDuration(a.duration) - parseDuration(b.duration));
        document.getElementById('sortByDuration')?.classList.add('active');
    }
    displayFlightCards(currentFlights);
}

function buildFlightCard(flight, index) {
    const card = document.createElement('div');
    card.className = 'flight-card';

    const hasConversion = flight.original_currency && flight.original_currency !== flight.currency;
    const priceSubtitle = hasConversion
        ? `Converted from ${flight.original_currency} ${flight.original_price}`
        : `Total price for ${flight.trip_type}`;
    const bestDeal = index === 0 ? '<span class="badge badge-best">Best Deal</span>' : '';
    const stops = flight.stops !== undefined
        ? (flight.stops === 0 ? 'Direct' : `${flight.stops} stop${flight.stops > 1 ? 's' : ''}`)
        : '';

    let details = `<div class="detail-item"><div class="detail-label">Airline</div><div class="detail-value airline-info"><span class="airline-code">${flight.airline}</span><span>${flight.flight_number}</span></div></div><div class="detail-item"><div class="detail-label">Departure</div><div class="detail-value">${formatDate(flight.departure_date)}</div></div>`;
    if (flight.return_date) details += `<div class="detail-item"><div class="detail-label">Return</div><div class="detail-value">${formatDate(flight.return_date)}</div></div>`;
    if (flight.duration) details += `<div class="detail-item"><div class="detail-label">Duration</div><div class="detail-value">${formatDuration(flight.duration)}</div></div>`;
    if (stops) details += `<div class="detail-item"><div class="detail-label">Stops</div><div class="detail-value">${stops}</div></div>`;

    card.innerHTML = `<div class="flight-header"><div class="flight-price-section"><div class="flight-price">${flight.currency} ${flight.price}</div><div class="price-subtitle">${priceSubtitle}</div></div><div class="flight-badges">${bestDeal}<span class="badge badge-type">${flight.trip_type}</span></div></div><div class="flight-details">${details}</div><button class="book-btn" onclick="window.open('${flight.booking_url}','_blank')">Book Flight</button>`;
    return card;
}
