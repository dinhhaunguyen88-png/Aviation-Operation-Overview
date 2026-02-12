/**
 * Aviation Operations Dashboard - JavaScript
 * Phase 3: Core Features
 */

// =====================================================
// Configuration
// =====================================================

const API_BASE = '';  // Same origin
const REFRESH_INTERVAL = 60000;  // 1 minute

// State
let state = {
    selectedDate: new Date().toISOString().split('T')[0],
    dataSource: 'AIMS',
    aircraftFilter: '',
    flightLimit: '20',
    isLoading: false,
    dataWindow: { min_date: null, max_date: null, today: null }
};

// =====================================================
// Utility Functions
// =====================================================

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

function formatShortDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return `${date.getDate()}/${date.getMonth() + 1}/${date.getFullYear()}`;
}

// Airport timezone offsets (UTC offset in hours)
// Times in AIMS are stored in LOCAL STATION TIME already
// This map is for reference/future use if we need to convert
const AIRPORT_TIMEZONES = {
    // Vietnam (UTC+7)
    'SGN': 7, 'HAN': 7, 'DAD': 7, 'CXR': 7, 'PQC': 7, 'VCA': 7,
    'HPH': 7, 'HUI': 7, 'VCL': 7, 'UIH': 7, 'TBB': 7, 'PXU': 7,
    'VDO': 7, 'VII': 7, 'VKG': 7, 'BMV': 7, 'DLI': 7, 'VCS': 7,
    // Asia
    'BKK': 7, 'DMK': 7,  // Thailand
    'SIN': 8,             // Singapore
    'KUL': 8, 'PEN': 8,   // Malaysia
    'HKG': 8,             // Hong Kong
    'ICN': 9, 'GMP': 9,   // Korea
    'NRT': 9, 'HND': 9, 'KIX': 9, 'NGO': 9, 'FUK': 9, // Japan
    'TPE': 8, 'KHH': 8,   // Taiwan
    'PEK': 8, 'PVG': 8, 'CAN': 8, 'CTU': 8, 'XIY': 8, 'SZX': 8, // China
    'DEL': 5.5, 'BOM': 5.5, 'MAA': 5.5, // India
    'MNL': 8,             // Philippines
    'CGK': 7, 'DPS': 8,   // Indonesia
    'REP': 7, 'PNH': 7,   // Cambodia
    'RGN': 6.5,           // Myanmar
    'VTE': 7,             // Laos
    // Middle East
    'DXB': 4, 'DOH': 3, 'AUH': 4,
    // Europe
    'LHR': 0, 'CDG': 1, 'FRA': 1, 'AMS': 1,
    // Australia
    'SYD': 11, 'MEL': 11, 'BNE': 10
};

function formatTime(timeStr) {
    if (!timeStr) return '--:--';
    return timeStr.substring(0, 5);
}

// Format time string to HH:mm (Local Station Time)
function convertToLocalTime(timeStr, airportCode, flightObject) {
    if (!flightObject) return timeStr ? timeStr.substring(0, 5) : '--:--';

    // Map time fields to their pre-calculated local versions from backend
    const localMap = {
        [flightObject.std]: flightObject.local_std,
        [flightObject.sta]: flightObject.local_sta,
        [flightObject.etd]: flightObject.local_etd,
        [flightObject.eta]: flightObject.local_eta,
        [flightObject.tkof]: flightObject.local_tkof,
        [flightObject.tdwn]: flightObject.local_tdwn,
        [flightObject.atd]: flightObject.local_atd,
        [flightObject.ata]: flightObject.local_ata
    };

    if (localMap[timeStr]) return localMap[timeStr];

    if (!timeStr) return '--:--';
    return timeStr.substring(0, 5);
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

async function apiCall(endpoint, options = {}) {
    try {
        const url = `${API_BASE}${endpoint}`;
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': window.API_KEY || '',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'API request failed');
        }

        return data.data;
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message, 'error');
        throw error;
    }
}

// =====================================================
// Dashboard Data Loading
// =====================================================

async function loadDashboardSummary() {
    try {
        const data = await apiCall(`/api/dashboard/summary?date=${state.selectedDate}`);

        // Update KPI cards
        const updateKPI = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        // Crew Call Sick (SL + CSL with position breakdown)
        updateKPI('crew-sick-total', data.crew_sick_total || 0);
        const bp = data.crew_sick_by_position || {};
        const detailEl = document.getElementById('crew-sick-detail');
        if (detailEl) {
            detailEl.textContent = `CPT:${bp.CPT || 0}  FO:${bp.FO || 0}  PU:${bp.PU || 0}  FA:${bp.FA || 0}`;
        }

        updateKPI('total-ac-operation', data.total_aircraft_operation || 0);

        // KPI 3: A/C Breakdown (Use innerHTML for formatting)
        const acEl = document.getElementById('ac-type-hour');
        if (acEl) acEl.innerHTML = data.ac_type_breakdown || (data.total_block_hours || 0).toFixed(1);

        // KPI 4: Total Completed Flights
        updateKPI('total-completed', data.total_completed_flights || 0);

        updateKPI('total-flights', data.total_flights || 0);
        updateKPI('total-block-hours', (data.total_block_hours || 0).toFixed(1));
        updateKPI('pax-load', data.total_pax ? data.total_pax.toLocaleString() : '0');
        updateKPI('otp-percent', (data.otp_percentage || 0).toFixed(1) + '%');

        // Update last sync time
        const syncEl = document.getElementById('last-sync');
        if (syncEl) {
            syncEl.textContent = `Last sync: ${new Date().toLocaleTimeString('vi-VN')}`;
        }

    } catch (error) {
        console.error('Failed to load dashboard summary:', error);
    }
}

async function loadStandbyData() {
    try {
        const data = await apiCall(`/api/standby?date=${state.selectedDate}`);

        // Update standby stats
        const byStatus = data.by_status || {};
        const updateStat = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        updateStat('sby-available', (byStatus.SBY?.count) || 0);
        updateStat('sl-count', (byStatus.SL?.count) || 0);
        updateStat('csl-count', (byStatus.CSL?.count) || 0);

        // Render standby list
        const listContainer = document.getElementById('standby-list');
        if (listContainer) {
            const standbyItems = data.standby || [];
            if (standbyItems.length > 0) {
                listContainer.innerHTML = standbyItems.map(item => `
                    <div class="standby-item">
                        <span>${item.crew_name || item.crew_id}</span>
                        <span class="badge badge-${item.status === 'SBY' ? 'success' : 'warning'}">${item.status}</span>
                    </div>
                `).join('');
            } else {
                listContainer.innerHTML = '<div class="empty-state">No standby data for this date</div>';
            }
        }

    } catch (error) {
        console.error('Failed to load standby data:', error);
    }
}

async function loadFTLSummary() {
    try {
        const data = await apiCall(`/api/ftl/summary?date=${state.selectedDate}`);

        // Update FTL stats
        const updateStat = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        updateStat('ftl-normal', data.by_level?.NORMAL || 0);
        updateStat('ftl-warning', data.by_level?.WARNING || 0);
        updateStat('ftl-critical', data.by_level?.CRITICAL || 0);

        // Update compliance rate
        const complianceRate = data.compliance_rate || 100;
        const rateEl = document.getElementById('compliance-rate');
        if (rateEl) {
            rateEl.textContent = `${complianceRate}%`;
            rateEl.className = 'badge';
            if (complianceRate >= 95) {
                rateEl.classList.add('badge-success');
            } else if (complianceRate >= 85) {
                rateEl.classList.add('badge-warning');
            } else {
                rateEl.classList.add('badge-danger');
            }
        }

        const gaugeEl = document.getElementById('gauge-fill');
        if (gaugeEl) gaugeEl.style.width = `${complianceRate}%`;

        // Render FTL tables
        renderFTLTable('ftl-28d-tbody', data.top_20_28_day || [], 'hours_28_day');
        renderFTLTable('ftl-12m-tbody', data.top_20_12_month || [], 'hours_12_month');

    } catch (error) {
        console.error('Failed to load FTL summary:', error);
    }
}

function getFlightStatusClass(status) {
    switch (status?.toLowerCase()) {
        case 'departed': return 'info';
        case 'arrived': return 'success';
        case 'delayed': return 'warning';
        case 'cancelled': return 'danger';
        default: return 'secondary';
    }
}

async function loadFlights() {
    try {
        let url = `/api/flights?date=${state.selectedDate}`;
        if (state.aircraftFilter) {
            url += `&aircraft_type=${state.aircraftFilter}`;
        }

        const data = await apiCall(url);
        const tbody = document.getElementById('flights-tbody');
        let flights = data.flights || [];

        // Populate aircraft type filter dynamically
        const acTypes = new Set();
        flights.forEach(f => { if (f.aircraft_type) acTypes.add(f.aircraft_type.trim()); });
        populateAircraftTypeDropdown('aircraft-filter', acTypes);

        // Note: API returns ops day flights (prev + today + next day)
        // No additional frontend filtering needed - API handles date filtering

        // Current time for proximity calculations
        const now = new Date();
        const limit = state.flightLimit || '20';

        // Helper: Parse flight time to Date object
        // Create local date for comparison - handles overnight flights correctly
        const parseFlightTime = (flight) => {
            const timeStr = flight.local_std || flight.std;
            if (!timeStr) return null;

            try {
                const timeParts = timeStr.split(':');
                const hours = parseInt(timeParts[0]);
                const minutes = parseInt(timeParts[1]);

                // Use local_flight_date if available (more accurate for overnight flights)
                // Otherwise use flight_date and adjust for overnight window (00:00-03:59 = next day)
                let dateStr = flight.local_flight_date || flight.flight_date;
                const flightDate = new Date(dateStr);

                // If local_flight_date is not available but local_std is before 04:00,
                // this is an overnight flight - add 1 day to flight_date
                if (!flight.local_flight_date && hours < 4) {
                    flightDate.setDate(flightDate.getDate() + 1);
                }

                flightDate.setHours(hours, minutes, 0, 0);
                return flightDate;
            } catch (e) {
                return null;
            }
        };


        // Add parsed time to each flight
        flights = flights.map(f => ({
            ...f,
            _flightTime: parseFlightTime(f),
            _timeDiff: parseFlightTime(f) ? parseFlightTime(f) - now : Infinity
        }));

        // Filter out flights without valid time
        const validFlights = flights.filter(f => f._flightTime !== null);

        let displayFlights = [];

        if (limit === '20' || limit === '30') {
            // "Operational Focus" logic: 2h before, 1h after now
            // Focus on approximately 30 flights centered on Now
            const twoHoursAgo = now.getTime() - (2 * 60 * 60 * 1000);
            const oneHourHence = now.getTime() + (1 * 60 * 60 * 1000);

            // Flights within the (-2h, +1h) window
            let focusFlights = validFlights.filter(f =>
                f._flightTime.getTime() >= twoHoursAgo && f._flightTime.getTime() <= oneHourHence
            );

            if (focusFlights.length < 15) {
                // If window is too sparse, just take the 30 closest to Now
                displayFlights = validFlights
                    .sort((a, b) => Math.abs(a._timeDiff) - Math.abs(b._timeDiff))
                    .slice(0, 30)
                    .sort((a, b) => a._flightTime - b._flightTime);
            } else {
                // If window is too busy, prioritize those closest to Now to keep it around ~30-40
                if (focusFlights.length > 50) {
                    displayFlights = focusFlights
                        .sort((a, b) => Math.abs(a._timeDiff) - Math.abs(b._timeDiff))
                        .slice(0, 40) // Give a bit more if it's busy
                        .sort((a, b) => a._flightTime - b._flightTime);
                } else {
                    displayFlights = focusFlights.sort((a, b) => a._flightTime - b._flightTime);
                }
            }
        } else if (limit === 'all') {
            // Show all, sorted by STD
            displayFlights = validFlights.sort((a, b) => a._flightTime - b._flightTime);
        } else {
            // 50, 100, 200 logic:
            const numLimit = parseInt(limit);

            // Priority 1: Current/Upcoming window focus
            // Priority 2: Others sorted by time proximity
            displayFlights = validFlights
                .sort((a, b) => {
                    // Sort primarily by closeness to NOW, but keep chronological feel
                    return Math.abs(a._timeDiff) - Math.abs(b._timeDiff);
                })
                .slice(0, numLimit)
                .sort((a, b) => a._flightTime - b._flightTime);
        }

        if (displayFlights.length > 0) {
            tbody.innerHTML = displayFlights.map(flight => {
                const dep = flight.departure || '';
                const arr = flight.arrival || '';
                return `
                <tr>
                    <td class="cell-date">${formatShortDate(flight.local_flight_date || flight.flight_date)}</td>

                    <td class="cell-flt">${flight.flight_number || ''}</td>
                    <td class="cell-reg">${flight.aircraft_reg || '-'}</td>
                    <td class="cell-ac">${flight.aircraft_type || '-'}</td>
                    <td class="cell-dep">${dep}</td>
                    <td class="cell-arr">${arr}</td>
                    <td class="cell-time">${convertToLocalTime(flight.std, dep, flight)}</td>
                    <td class="cell-time">${convertToLocalTime(flight.sta, arr, flight)}</td>
                    <td class="cell-time">${convertToLocalTime(flight.etd, dep, flight)}</td>
                    <td class="cell-time">${convertToLocalTime(flight.eta, arr, flight)}</td>
                    <td class="cell-time">${convertToLocalTime(flight.atd, dep, flight)}</td>
                    <td class="cell-time">${convertToLocalTime(flight.tkof, dep, flight)}</td>
                    <td class="cell-time">${convertToLocalTime(flight.tdwn, arr, flight)}</td>
                    <td class="cell-time">${convertToLocalTime(flight.ata, arr, flight)}</td>
                </tr>
            `}).join('');
        } else {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="14">No flight data found for this selection</td></tr>';
        }

    } catch (error) {
        console.error('Failed to load flights:', error);
        document.getElementById('flights-tbody').innerHTML =
            '<tr class="empty-row"><td colspan="14">Failed to load flight data</td></tr>';
    }
}

// =====================================================
// Render Functions
// =====================================================



function renderFTLTable(tbodyId, data, hoursField) {
    const tbody = document.getElementById(tbodyId);

    if (data.length > 0) {
        tbody.innerHTML = data.map((crew, index) => `
            <tr>
                <td>${index + 1}</td>
                <td>${crew.crew_name || crew.crew_id}</td>
                <td>${crew[hoursField] || 0}</td>
                <td><span class="badge badge-${getWarningBadgeClass(crew.warning_level)}">${crew.warning_level || 'NORMAL'}</span></td>
            </tr>
        `).join('');
    } else {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No data</td></tr>';
    }
}

// =====================================================
// Helper Functions
// =====================================================

function getStatusBadgeClass(status) {
    switch (status) {
        case 'FLY': return 'info';
        case 'SBY': return 'success';
        case 'SL':
        case 'CSL': return 'warning';
        case 'OFF': return 'secondary';
        default: return 'secondary';
    }
}

function getWarningBadgeClass(level) {
    switch (level) {
        case 'NORMAL': return 'success';
        case 'WARNING': return 'warning';
        case 'CRITICAL': return 'danger';
        default: return 'success';
    }
}

function getFlightStatusClass(status) {
    switch (status?.toLowerCase()) {
        case 'departed': return 'info';
        case 'arrived': return 'success';
        case 'delayed': return 'warning';
        case 'cancelled': return 'danger';
        default: return 'secondary';
    }
}

// =====================================================
// Data Source Toggle
// =====================================================

async function setDataSource(source) {
    try {
        await apiCall('/api/config/datasource', {
            method: 'POST',
            body: JSON.stringify({ source })
        });

        state.dataSource = source;

        // Update UI
        document.getElementById('btn-aims').classList.toggle('active', source === 'AIMS');
        document.getElementById('btn-csv').classList.toggle('active', source === 'CSV');
        document.getElementById('data-source-label').textContent = `Source: ${source}`;

        // Update sync status
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');

        if (source === 'AIMS') {
            statusDot.className = 'status-dot online';
            statusText.textContent = 'Connected';
        } else {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'CSV Mode';
        }

        showToast(`Data source changed to ${source}`, 'success');

        // Reload data
        refreshAll();

    } catch (error) {
        console.error('Failed to set data source:', error);
    }
}

// =====================================================
// Upload Functions
// =====================================================

function openUploadModal() {
    document.getElementById('upload-modal').classList.add('active');
}

function closeUploadModal() {
    document.getElementById('upload-modal').classList.remove('active');
}

async function handleUpload() {
    const fileInput = document.getElementById('csv-file');
    const fileType = document.getElementById('upload-type').value;

    if (!fileInput.files.length) {
        showToast('Please select a file', 'warning');
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', fileType);

    try {
        const response = await fetch('/api/upload/csv', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            showToast(`Uploaded ${result.data.records_count} records`, 'success');
            closeUploadModal();
            refreshAll();
        } else {
            showToast(result.error || 'Upload failed', 'error');
        }

    } catch (error) {
        console.error('Upload failed:', error);
        showToast('Upload failed', 'error');
    }
}

// =====================================================
// Main Functions
// =====================================================

async function loadDataWindow() {
    try {
        const data = await apiCall('/api/data-window');
        state.dataWindow = data;

        // Constrain date picker
        const dateInput = document.getElementById('filter-date');
        if (dateInput && data.min_date) dateInput.min = data.min_date;
        if (dateInput && data.max_date) dateInput.max = data.max_date;

        updateDateNavButtons();
        console.log('Data window loaded:', data);
    } catch (error) {
        console.warn('Could not load data window:', error);
    }
}

function navigateDate(offset) {
    const current = new Date(state.selectedDate);
    current.setDate(current.getDate() + offset);
    const newDate = current.toISOString().split('T')[0];

    // Enforce window boundaries
    if (state.dataWindow.min_date && newDate < state.dataWindow.min_date) return;
    if (state.dataWindow.max_date && newDate > state.dataWindow.max_date) return;

    state.selectedDate = newDate;
    document.getElementById('filter-date').value = newDate;
    updateDateNavButtons();
    refreshAll();
}

function updateDateNavButtons() {
    const prevBtn = document.getElementById('date-prev-btn');
    const nextBtn = document.getElementById('date-next-btn');
    const todayBtn = document.getElementById('date-today-btn');

    if (prevBtn && state.dataWindow.min_date) {
        prevBtn.disabled = (state.selectedDate <= state.dataWindow.min_date);
    }
    if (nextBtn && state.dataWindow.max_date) {
        nextBtn.disabled = (state.selectedDate >= state.dataWindow.max_date);
    }
    if (todayBtn && state.dataWindow.today) {
        todayBtn.style.display = (state.selectedDate === state.dataWindow.today) ? 'none' : '';
    }
}

async function refreshAll() {
    if (state.isLoading) return;

    state.isLoading = true;

    try {
        await Promise.all([
            loadDashboardSummary(),
            loadFlights(),
            loadFTLSummary(),
            loadStandbyData()
        ]);
    } catch (error) {
        console.error('Refresh failed:', error);
    } finally {
        state.isLoading = false;
    }
}

function initializeDashboard() {
    // Set initial date
    const dateInput = document.getElementById('filter-date');
    dateInput.value = state.selectedDate;

    // Date picker change
    dateInput.addEventListener('change', (e) => {
        state.selectedDate = e.target.value;
        updateDateNavButtons();
        refreshAll();
    });

    // Date navigation buttons
    document.getElementById('date-prev-btn').addEventListener('click', () => navigateDate(-1));
    document.getElementById('date-next-btn').addEventListener('click', () => navigateDate(1));
    document.getElementById('date-today-btn').addEventListener('click', () => {
        if (state.dataWindow.today) {
            state.selectedDate = state.dataWindow.today;
            dateInput.value = state.dataWindow.today;
            updateDateNavButtons();
            refreshAll();
        }
    });

    document.getElementById('refresh-btn').addEventListener('click', refreshAll);

    document.getElementById('btn-aims').addEventListener('click', () => setDataSource('AIMS'));
    document.getElementById('btn-csv').addEventListener('click', () => setDataSource('CSV'));

    document.getElementById('aircraft-filter').addEventListener('change', (e) => {
        state.aircraftFilter = e.target.value;
        loadFlights();
    });

    // Flight limit filter listener
    document.getElementById('flight-limit').addEventListener('change', (e) => {
        state.flightLimit = e.target.value;
        console.log('Flight limit changed to:', state.flightLimit);
        loadFlights();
    });

    // Focus Mode listener
    const focusModeBtn = document.getElementById('focus-mode-btn');
    if (focusModeBtn) {
        focusModeBtn.addEventListener('click', (e) => {
            const btn = e.currentTarget;
            const section = document.getElementById('charts-section');
            if (section) {
                btn.classList.toggle('active');
                section.classList.toggle('hidden');
                window.dispatchEvent(new Event('resize'));
            }
        });
    }

    // Upload modal
    const uploadZone = document.getElementById('upload-zone');
    const csvInput = document.getElementById('csv-file');

    uploadZone.addEventListener('click', () => csvInput.click());
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--primary)';
    });
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.style.borderColor = 'var(--border)';
    });
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--border)';
        if (e.dataTransfer.files.length) {
            csvInput.files = e.dataTransfer.files;
        }
    });

    document.getElementById('modal-close').addEventListener('click', closeUploadModal);
    document.getElementById('cancel-upload').addEventListener('click', closeUploadModal);
    document.getElementById('submit-upload').addEventListener('click', handleUpload);

    // Initial load: fetch data window first, then all data
    initCharts();
    loadDataWindow().then(() => refreshAll());

    // Auto-refresh
    setInterval(refreshAll, REFRESH_INTERVAL);

    console.log('Dashboard initialized with 7-day data window');
}

// Chart logic removed as requested (Departure Slots Chart)
function updateCharts(data) {
    // No charts to update currently
}

function initCharts() {
    console.log('[DEBUG] initCharts - No charts to initialize');
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initializeDashboard);


// =====================================================
// Aircraft Modal Functions
// =====================================================

function openAircraftModal() {
    const modal = document.getElementById('aircraft-modal');
    if (modal) {
        modal.style.display = 'flex';
        loadAircraftData();
    }
}

function closeAircraftModal() {
    const modal = document.getElementById('aircraft-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function loadAircraftData() {
    const tbody = document.getElementById('aircraft-table-body');
    const totalSpan = document.getElementById('aircraft-total');
    const typeFilter = document.getElementById('ac-type-filter');
    const selectedType = typeFilter ? typeFilter.value : '';

    try {
        const data = await apiCall(`/api/aircraft/daily-summary?date=${state.selectedDate}`);

        if (!data.aircraft || data.aircraft.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center;">No aircraft data</td></tr>';
            totalSpan.textContent = 'Total: 0 aircraft';
            return;
        }

        // Filter by selected type
        // Populate ac-type-filter dropdown dynamically
        const modalTypes = new Set();
        data.aircraft.forEach(ac => { if (ac.type) modalTypes.add(ac.type.trim()); });
        populateAircraftTypeDropdown('ac-type-filter', modalTypes);

        let filteredAircraft = data.aircraft;
        if (selectedType) {
            filteredAircraft = data.aircraft.filter(ac => {
                // Exact match for type (case insensitive)
                const acType = (ac.type || '').toString().toUpperCase().trim();
                const filterType = selectedType.toUpperCase().trim();
                return acType === filterType;
            });
        }

        let html = '';
        filteredAircraft.forEach(ac => {
            const statusClass = ac.status === 'FLYING' ? 'status-active' : 'status-ground';
            const statusIcon = ac.status === 'FLYING' ? '✈️' : '🅿️';

            html += `
                <tr data-type="${ac.type}">
                    <td><strong>${ac.reg}</strong></td>
                    <td>${ac.type}</td>
                    <td style="text-align: center;">${ac.flight_count}</td>
                    <td style="text-align: center;">${ac.block_hours}h</td>
                    <td style="text-align: center;">${ac.utilization}%</td>
                    <td>${ac.first_flight} → ${ac.last_flight}</td>
                    <td class="${statusClass}">${statusIcon} ${ac.status}</td>
                </tr>
            `;
        });

        tbody.innerHTML = html || '<tr><td colspan="7" style="text-align: center;">No matching aircraft</td></tr>';
        totalSpan.textContent = `Showing: ${filteredAircraft.length} / ${data.total} aircraft`;

    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #ff6b6b;">Failed to load data</td></tr>';
    }
}

// Setup Aircraft Modal Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Click on Aircraft Operation card
    const acCard = document.getElementById('aircraft-operation-card');
    if (acCard) {
        acCard.addEventListener('click', openAircraftModal);
    }

    // Close button
    const closeBtn = document.getElementById('close-aircraft-modal');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeAircraftModal);
    }

    // Click outside to close
    const modal = document.getElementById('aircraft-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAircraftModal();
            }
        });
    }

    // Type filter change
    const typeFilter = document.getElementById('ac-type-filter');
    if (typeFilter) {
        typeFilter.addEventListener('change', loadAircraftData);
    }

    // === Completed Flights Modal Event Listeners ===
    const completedCard = document.getElementById('flights-completed-card');
    if (completedCard) {
        completedCard.addEventListener('click', openCompletedFlightsModal);
    }

    const closeCompletedBtn = document.getElementById('close-completed-modal');
    if (closeCompletedBtn) {
        closeCompletedBtn.addEventListener('click', closeCompletedFlightsModal);
    }

    const completedModal = document.getElementById('completed-flights-modal');
    if (completedModal) {
        completedModal.addEventListener('click', (e) => {
            if (e.target === completedModal) {
                closeCompletedFlightsModal();
            }
        });
    }
});

// =====================================================
// Dynamic Aircraft Type Dropdown Population
// =====================================================

function populateAircraftTypeDropdown(selectId, types) {
    const select = document.getElementById(selectId);
    if (!select) return;
    const currentValue = select.value;
    // Keep the first "All" option, remove the rest
    while (select.options.length > 1) {
        select.remove(1);
    }
    // Sort types alphabetically
    const sorted = [...types].sort();
    sorted.forEach(type => {
        const opt = document.createElement('option');
        opt.value = type;
        opt.textContent = type;
        select.appendChild(opt);
    });
    // Restore selection if still valid
    if (currentValue && sorted.includes(currentValue)) {
        select.value = currentValue;
    }
}

// =====================================================
// Completed Flights Modal Functions
// =====================================================

function openCompletedFlightsModal() {
    const modal = document.getElementById('completed-flights-modal');
    if (modal) {
        modal.style.display = 'flex';
        loadCompletedFlightsData();
    }
}

function closeCompletedFlightsModal() {
    const modal = document.getElementById('completed-flights-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function loadCompletedFlightsData() {
    const tbody = document.getElementById('completed-flights-tbody');
    const totalSpan = document.getElementById('completed-flights-total');
    const summarySpan = document.getElementById('completed-flights-summary');

    try {
        const data = await apiCall(`/api/flights/completed?date=${state.selectedDate}`);
        const flights = data.completed_flights || [];

        if (summarySpan) {
            summarySpan.textContent = `${data.total_completed} / ${data.total_flights} flights completed (${data.date})`;
        }

        if (flights.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align: center;">No completed flights</td></tr>';
            totalSpan.textContent = 'Total: 0 completed';
            return;
        }

        const methodBadge = (method) => {
            const colors = {
                'ATA': 'success',
                'STATUS+ATD': 'success',
                'ATD+Buffer': 'info',
                'STA+30': 'warning',
                'PAST_DATE': 'secondary'
            };
            return `<span class="badge badge-${colors[method] || 'secondary'}">${method}</span>`;
        };

        tbody.innerHTML = flights.map((f, i) => `
            <tr>
                <td>${i + 1}</td>
                <td><strong>${f.flight_number}</strong></td>
                <td>${f.aircraft_reg}</td>
                <td>${f.aircraft_type}</td>
                <td>${f.route}</td>
                <td>${f.std || '--:--'}</td>
                <td>${f.sta || '--:--'}</td>
                <td>${f.atd || '--:--'}</td>
                <td>${f.ata || '--:--'}</td>
                <td>${methodBadge(f.completion_source)}</td>
            </tr>
        `).join('');

        totalSpan.textContent = `Total: ${flights.length} completed`;

    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: #ff6b6b;">Failed to load data</td></tr>';
    }
}

