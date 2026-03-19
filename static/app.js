document.addEventListener("DOMContentLoaded", () => {
    fetchData();
    // Poll every 5 seconds
    setInterval(fetchData, 5000);
});

async function fetchData() {
    try {
        const [devicesRes, discoveredRes] = await Promise.all([
            fetch('/api/devices'),
            fetch('/api/discovered')
        ]);
        
        if (devicesRes.ok) {
            const devices = await devicesRes.json();
            renderRegistered(devices);
        }
        
        if (discoveredRes.ok) {
            const discovered = await discoveredRes.json();
            renderDiscovered(discovered);
        }
    } catch (e) {
        console.error("Error fetching data:", e);
    }
}

function renderRegistered(devices) {
    const list = document.getElementById('registered-list');
    const countBadge = document.getElementById('registered-count');
    
    countBadge.innerText = devices.length;
    
    if (devices.length === 0) {
        list.innerHTML = '<div class="empty-state">No devices registered. Add one from the right pane.</div>';
        return;
    }
    
    // Create a Set of existing cards to keep inputs focused if typing
    const existingCards = new Set(Array.from(list.children).map(c => c.id));
    let html = '';
    
    devices.forEach(dev => {
        const temp = dev.current_temp_f !== null ? `${dev.current_temp_f.toFixed(1)}°F` : '--';
        const hum = dev.current_humidity !== null ? `${dev.current_humidity.toFixed(1)}%` : '--';
        
        let timeStr = 'Never';
        if (dev.last_seen) {
            const date = new Date(dev.last_seen * 1000);
            timeStr = date.toLocaleTimeString();
        }

        const cardId = `reg-card-${dev.mac_address.replace(/:/g, '')}`;
        
        // Only re-render if it doesn't exist to prevent input losing focus, OR we use a smarter approach.
        // For simplicity in vanilla JS: we update Text nodes rather than innerHTML if possible.
        // But to build fast: we'll rebuild it if it's not present, and if it's present, update only the text spans.
        let card = document.getElementById(cardId);
        
        if (!card) {
            card = document.createElement('div');
            card.className = 'device-card';
            card.id = cardId;
            card.innerHTML = `
                <div class="card-top">
                    <div class="device-info">
                        <h3>
                            <span class="material-symbols-outlined">device_thermostat</span> 
                            <input type="text" class="dev-name-input" id="name-${dev.mac_address}" value="${escapeHTML(dev.name)}">
                            <span class="mac-label">${dev.mac_address}</span>
                        </h3>
                        <div class="measurement-pill temp">
                            <span class="material-symbols-outlined">thermometer</span> <span class="val-temp">${temp}</span>
                        </div>
                        <div class="measurement-pill hum">
                            <span class="material-symbols-outlined">water_drop</span> <span class="val-hum">${hum}</span>
                        </div>
                        <div class="last-seen">Last updated: <span class="val-time">${timeStr}</span></div>
                    </div>
                </div>
                <div class="thresholds-form">
                    <div class="form-group">
                        <label>Min Temp (°F)</label>
                        <input type="number" id="min-temp-${dev.mac_address}" value="${dev.min_temp !== null ? dev.min_temp : ''}">
                    </div>
                    <div class="form-group">
                        <label>Max Temp (°F)</label>
                        <input type="number" id="max-temp-${dev.mac_address}" value="${dev.max_temp !== null ? dev.max_temp : ''}">
                    </div>
                    <div class="form-group">
                        <label>Min Humidity (%)</label>
                        <input type="number" id="min-hum-${dev.mac_address}" value="${dev.min_hum !== null ? dev.min_hum : ''}">
                    </div>
                    <div class="form-group">
                        <label>Max Humidity (%)</label>
                        <input type="number" id="max-hum-${dev.mac_address}" value="${dev.max_hum !== null ? dev.max_hum : ''}">
                    </div>
                </div>
                <div class="card-actions">
                    <button class="btn-remove" onclick="removeDevice('${dev.mac_address}')">Remove</button>
                    <button class="btn-save" onclick="updateDevice('${dev.mac_address}')">Save Device Configuration</button>
                </div>
            `;
            list.appendChild(card);
        } else {
            // Update only volatile data
            card.querySelector('.val-temp').innerText = temp;
            card.querySelector('.val-hum').innerText = hum;
            card.querySelector('.val-time').innerText = timeStr;
        }
        
        existingCards.delete(cardId);
    });
    
    // Remove old cards
    existingCards.forEach(id => {
        if(id) document.getElementById(id)?.remove();
    });
    
    // Remove empty state if present and cards exist
    const emptyState = list.querySelector('.empty-state');
    if (emptyState && devices.length > 0 && list.children.length > 1) {
        emptyState.remove();
    }
}

function renderDiscovered(devices) {
    const list = document.getElementById('discovered-list');
    if (devices.length === 0) {
        list.innerHTML = '<div class="empty-state">No new devices nearby. Scanning...</div>';
        return;
    }
    
    let html = '';
    devices.forEach(dev => {
        const timeStr = new Date(dev.timestamp * 1000).toLocaleTimeString();
        html += `
            <div class="device-card">
                <div class="card-top">
                    <div class="device-info">
                        <h3>${escapeHTML(dev.name)} <span class="mac-label">${dev.mac_address}</span></h3>
                        <div class="measurement-pill temp">
                            <span class="material-symbols-outlined">thermometer</span> ${dev.temp_f.toFixed(1)}°F
                        </div>
                        <div class="measurement-pill hum">
                            <span class="material-symbols-outlined">water_drop</span> ${dev.humidity.toFixed(1)}%
                        </div>
                        <div class="last-seen">Heard: ${timeStr}</div>
                    </div>
                    <button class="btn-success" onclick="addDevice('${dev.mac_address}', '${escapeHTML(dev.name)}')">
                        <span class="material-symbols-outlined">add</span>
                    </button>
                </div>
            </div>
        `;
    });
    list.innerHTML = html;
}

async function addDevice(mac, name) {
    const payload = {
        mac_address: mac,
        name: name
    };
    await fetch('/api/devices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    fetchData(); // Refresh immediately
}

async function updateDevice(mac) {
    const nameVal = document.getElementById(`name-${mac}`).value.trim() || "Unknown Sensor";
    const minT = document.getElementById(`min-temp-${mac}`).value;
    const maxT = document.getElementById(`max-temp-${mac}`).value;
    const minH = document.getElementById(`min-hum-${mac}`).value;
    const maxH = document.getElementById(`max-hum-${mac}`).value;
    
    const payload = {
        mac_address: mac,
        name: nameVal,
        min_temp: minT !== "" ? parseFloat(minT) : null,
        max_temp: maxT !== "" ? parseFloat(maxT) : null,
        min_hum: minH !== "" ? parseFloat(minH) : null,
        max_hum: maxH !== "" ? parseFloat(maxH) : null
    };
    
    await fetch(`/api/devices/${encodeURIComponent(mac)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    // Show success feedback
    const btn = event.target;
    const oldText = btn.innerText;
    btn.innerText = "Saved!";
    btn.style.background = "var(--success-color)";
    setTimeout(() => {
        btn.innerText = oldText;
        btn.style.background = "";
    }, 2000);
}

async function removeDevice(mac) {
    if(!confirm('Are you sure you want to remove this device?')) return;
    await fetch(`/api/devices/${encodeURIComponent(mac)}`, {
        method: 'DELETE'
    });
    // Remove the card from DOM immediately so it vanishes
    const cardId = `reg-card-${mac.replace(/:/g, '')}`;
    document.getElementById(cardId)?.remove();
    fetchData();
}

function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag]));
}
