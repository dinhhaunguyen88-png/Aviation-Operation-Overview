/**
 * Crew Detail Page JavaScript
 * Aviation Operations Dashboard
 */

// =====================================================
// State Management
// =====================================================

const state = {
    crewId: null,
    crewData: null,
    rosterData: [],
    flightsData: [],
    qualifications: [],
    currentMonth: new Date(),
    chartRange: 7
};

// =====================================================
// DOM Elements
// =====================================================

const elements = {
    crewIdBadge: document.getElementById('crewIdBadge'),
    avatarText: document.getElementById('avatarText'),
    crewName: document.getElementById('crewName'),
    crewPosition: document.getElementById('crewPosition'),
    crewBase: document.getElementById('crewBase'),
    crewStatus: document.getElementById('crewStatus'),
    hours28d: document.getElementById('hours28d'),
    hours12m: document.getElementById('hours12m'),
    warningLevel: document.getElementById('warningLevel'),
    calendarGrid: document.getElementById('calendarGrid'),
    currentMonth: document.getElementById('currentMonth'),
    chartBars: document.getElementById('chartBars'),
    chartLabels: document.getElementById('chartLabels'),
    flightsTableBody: document.getElementById('flightsTableBody'),
    qualsGrid: document.getElementById('qualsGrid')
};

// =====================================================
// Initialization
// =====================================================

document.addEventListener('DOMContentLoaded', () => {
    // Get crew ID from URL
    const params = new URLSearchParams(window.location.search);
    state.crewId = params.get('id');

    if (!state.crewId) {
        showError('No crew ID provided');
        return;
    }

    // Initialize
    initEventListeners();
    loadCrewData();
});

function initEventListeners() {
    // Month navigation
    document.getElementById('prevMonth').addEventListener('click', () => {
        state.currentMonth.setMonth(state.currentMonth.getMonth() - 1);
        loadRosterData();
    });

    document.getElementById('nextMonth').addEventListener('click', () => {
        state.currentMonth.setMonth(state.currentMonth.getMonth() + 1);
        loadRosterData();
    });

    // Chart range buttons
    document.querySelectorAll('.range-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            state.chartRange = parseInt(e.target.dataset.range);
            renderFlightHoursChart();
        });
    });
}

// =====================================================
// API Calls
// =====================================================

async function loadCrewData() {
    try {
        const response = await fetch(`/api/crew/${state.crewId}`, {
            headers: { 'X-API-Key': window.API_KEY || '' }
        });
        const result = await response.json();

        if (result.success) {
            state.crewData = result.data;
            renderCrewProfile();

            // Load related data
            loadRosterData();
            loadFlightHours();
            loadRecentFlights();
            loadQualifications();
        } else {
            showError(result.error || 'Failed to load crew data');
        }
    } catch (error) {
        console.error('Error loading crew data:', error);
        showError('Network error. Please try again.');
    }
}

async function loadRosterData() {
    const year = state.currentMonth.getFullYear();
    const month = state.currentMonth.getMonth() + 1;
    const fromDate = `${year}-${String(month).padStart(2, '0')}-01`;
    const toDate = new Date(year, month, 0).toISOString().split('T')[0];

    elements.currentMonth.textContent = state.currentMonth.toLocaleDateString('en-US', {
        month: 'long',
        year: 'numeric'
    });

    try {
        const response = await fetch(`/api/crew/${state.crewId}/roster?from=${fromDate}&to=${toDate}`, {
            headers: { 'X-API-Key': window.API_KEY || '' }
        });
        const result = await response.json();

        if (result.success) {
            state.rosterData = result.data || [];
            renderCalendar();
        }
    } catch (error) {
        console.error('Error loading roster:', error);
        renderCalendar();
    }
}

async function loadFlightHours() {
    try {
        const response = await fetch(`/api/crew/${state.crewId}/flight-hours`, {
            headers: { 'X-API-Key': window.API_KEY || '' }
        });
        const result = await response.json();

        if (result.success && result.data) {
            state.flightHours = result.data;
            renderFlightHoursChart();
        }
    } catch (error) {
        console.error('Error loading flight hours:', error);
    }
}

async function loadRecentFlights() {
    try {
        const response = await fetch(`/api/crew/${state.crewId}/flights?limit=10`, {
            headers: { 'X-API-Key': window.API_KEY || '' }
        });
        const result = await response.json();

        if (result.success) {
            state.flightsData = result.data || [];
            renderRecentFlights();
        }
    } catch (error) {
        console.error('Error loading flights:', error);
    }
}

async function loadQualifications() {
    try {
        const response = await fetch(`/api/crew/${state.crewId}/qualifications`, {
            headers: { 'X-API-Key': window.API_KEY || '' }
        });
        const result = await response.json();

        if (result.success) {
            state.qualifications = result.data || [];
            renderQualifications();
        }
    } catch (error) {
        console.error('Error loading qualifications:', error);
        renderQualifications();
    }
}

// =====================================================
// Render Functions
// =====================================================

function renderCrewProfile() {
    const crew = state.crewData;

    if (!crew) return;

    // Badge and avatar
    elements.crewIdBadge.textContent = crew.crew_id || state.crewId;
    elements.avatarText.textContent = getInitials(crew.crew_name || crew.first_name);

    // Name and position
    elements.crewName.textContent = crew.crew_name || `${crew.first_name || ''} ${crew.last_name || ''}`;
    elements.crewPosition.textContent = crew.rank || crew.position || 'Crew Member';

    // Badges
    elements.crewBase.textContent = crew.base || 'N/A';
    elements.crewStatus.textContent = crew.status || 'Active';

    // FTL stats
    elements.hours28d.textContent = formatHours(crew.hours_28_day || 0);
    elements.hours12m.textContent = formatHours(crew.hours_12_month || 0);

    const warningLevel = crew.warning_level || 'NORMAL';
    elements.warningLevel.textContent = warningLevel;
    elements.warningLevel.className = `stat-value warning-level ${warningLevel}`;

    // Personal info
    document.getElementById('infoCrewId').textContent = crew.crew_id || state.crewId;
    document.getElementById('infoGender').textContent = crew.gender === 'M' ? 'Male' : crew.gender === 'F' ? 'Female' : crew.gender || '--';
    document.getElementById('infoRank').textContent = crew.rank || '--';
    document.getElementById('infoSeniority').textContent = crew.seniority_date || '--';

    // Contact info
    document.getElementById('infoEmail').textContent = crew.email || '--';
    document.getElementById('infoPhone').textContent = crew.phone || '--';
    document.getElementById('infoCellPhone').textContent = crew.cell_phone || '--';
    document.getElementById('infoAddress').textContent = crew.address || '--';

    // Render FTL gauges
    renderFTLGauges(crew.hours_28_day || 0, crew.hours_12_month || 0);

    // Update page title
    document.title = `${crew.crew_name || 'Crew'} - Aviation Dashboard`;
}

function renderFTLGauges(hours28d, hours12m) {
    const limit28d = 100;
    const limit12m = 1000;

    const percent28d = Math.min((hours28d / limit28d) * 100, 100);
    const percent12m = Math.min((hours12m / limit12m) * 100, 100);

    // Update gauge fills
    const circumference = 2 * Math.PI * 45;

    const gauge28dFill = document.getElementById('gauge28dFill');
    const gauge12mFill = document.getElementById('gauge12mFill');

    if (gauge28dFill) {
        gauge28dFill.style.strokeDashoffset = circumference - (percent28d / 100) * circumference;
        if (percent28d >= 95) gauge28dFill.classList.add('critical');
        else if (percent28d >= 85) gauge28dFill.classList.add('warning');
    }

    if (gauge12mFill) {
        gauge12mFill.style.strokeDashoffset = circumference - (percent12m / 100) * circumference;
        if (percent12m >= 95) gauge12mFill.classList.add('critical');
        else if (percent12m >= 85) gauge12mFill.classList.add('warning');
    }

    document.getElementById('gauge28dValue').textContent = Math.round(percent28d) + '%';
    document.getElementById('gauge12mValue').textContent = Math.round(percent12m) + '%';
}

function renderCalendar() {
    const year = state.currentMonth.getFullYear();
    const month = state.currentMonth.getMonth();

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startingDay = (firstDay.getDay() + 6) % 7; // Monday = 0

    const rosterMap = {};
    state.rosterData.forEach(item => {
        const date = item.roster_date || item.date;
        if (date) {
            const day = new Date(date).getDate();
            rosterMap[day] = item;
        }
    });

    let html = '';

    // Empty cells before first day
    for (let i = 0; i < startingDay; i++) {
        html += '<div class="calendar-day empty"></div>';
    }

    // Days of month
    for (let day = 1; day <= lastDay.getDate(); day++) {
        const roster = rosterMap[day];
        const dutyCode = roster?.duty_code || roster?.status || '';
        const statusClass = getDutyClass(dutyCode);

        html += `
            <div class="calendar-day ${statusClass}" data-date="${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}">
                <span class="day-number">${day}</span>
                ${dutyCode ? `<span class="day-code">${dutyCode}</span>` : ''}
            </div>
        `;
    }

    elements.calendarGrid.innerHTML = html;
}

function getDutyClass(code) {
    if (!code) return '';

    const upperCode = code.toUpperCase();

    if (upperCode.includes('SBY') || upperCode.includes('STBY')) return 'sby';
    if (upperCode.includes('SL') || upperCode.includes('SICK')) return 'sl';
    if (upperCode.includes('OFF') || upperCode.includes('DO')) return 'off';
    if (upperCode.includes('TRN') || upperCode.includes('TRAIN')) return 'trn';
    if (upperCode.includes('FLY') || /^VN|^VJ|^\d/.test(upperCode)) return 'fly';

    return '';
}

function renderFlightHoursChart() {
    const days = state.chartRange;
    const dailyHours = state.flightHours?.daily || [];

    // Generate sample data if no data
    let chartData = [];

    if (dailyHours.length > 0) {
        chartData = dailyHours.slice(-days);
    } else {
        // Generate placeholder data
        for (let i = days - 1; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            chartData.push({
                date: date.toISOString().split('T')[0],
                hours: Math.random() * 8
            });
        }
    }

    const maxHours = Math.max(...chartData.map(d => d.hours || 0), 8);

    // Render bars
    let barsHtml = '';
    let labelsHtml = '';

    chartData.forEach(item => {
        const height = (item.hours / maxHours) * 100;
        const date = new Date(item.date);
        const label = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

        barsHtml += `<div class="chart-bar" style="height: ${height}%" data-value="${item.hours?.toFixed(1)}h"></div>`;
        labelsHtml += `<div class="chart-label">${label}</div>`;
    });

    elements.chartBars.innerHTML = barsHtml;
    elements.chartLabels.innerHTML = labelsHtml;
}

function renderRecentFlights() {
    if (state.flightsData.length === 0) {
        elements.flightsTableBody.innerHTML = '<tr><td colspan="6" class="loading-cell">No recent flights</td></tr>';
        return;
    }

    let html = '';

    state.flightsData.forEach(flight => {
        html += `
            <tr>
                <td>${flight.flight_date || flight.date || '--'}</td>
                <td>${flight.carrier_code || ''}${flight.flight_number || flight.flight_no || '--'}</td>
                <td>${flight.departure || flight.dep || '--'} → ${flight.arrival || flight.arr || '--'}</td>
                <td>${flight.std || '--'} - ${flight.sta || '--'}</td>
                <td>${flight.aircraft_type || flight.ac_type || '--'}</td>
                <td>${flight.position || flight.duty_code || '--'}</td>
            </tr>
        `;
    });

    elements.flightsTableBody.innerHTML = html;
}

function renderQualifications() {
    if (state.qualifications.length === 0) {
        elements.qualsGrid.innerHTML = '<div class="qual-card glass-card"><span style="color: var(--text-secondary);">No qualifications data</span></div>';
        return;
    }

    let html = '';
    const today = new Date();

    state.qualifications.forEach(qual => {
        const expiryDate = qual.expiry_date ? new Date(qual.expiry_date) : null;
        let expiryClass = 'valid';
        let expiryText = 'Valid';

        if (expiryDate) {
            const daysUntilExpiry = Math.floor((expiryDate - today) / (1000 * 60 * 60 * 24));

            if (daysUntilExpiry < 0) {
                expiryClass = 'expired';
                expiryText = 'Expired';
            } else if (daysUntilExpiry < 30) {
                expiryClass = 'expiring';
                expiryText = `Expires in ${daysUntilExpiry} days`;
            } else {
                expiryText = `Expires: ${expiryDate.toLocaleDateString()}`;
            }
        }

        html += `
            <div class="qual-card glass-card">
                <div class="qual-type">${qual.qual_type || qual.type || 'Qualification'}</div>
                <div class="qual-name">${qual.qual_name || qual.name || qual.qualification}</div>
                <div class="qual-expiry ${expiryClass}">${expiryText}</div>
            </div>
        `;
    });

    elements.qualsGrid.innerHTML = html;
}

// =====================================================
// Utility Functions
// =====================================================

function getInitials(name) {
    if (!name) return '--';
    return name.split(' ')
        .map(word => word.charAt(0).toUpperCase())
        .slice(0, 2)
        .join('');
}

function formatHours(hours) {
    if (typeof hours === 'number') {
        return hours.toFixed(1) + 'h';
    }
    return hours || '0h';
}

function showError(message) {
    elements.crewName.textContent = 'Error';
    elements.crewPosition.textContent = message;
    elements.crewIdBadge.textContent = 'Error';
}

// =====================================================
// Last Update
// =====================================================

document.getElementById('lastUpdate').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
