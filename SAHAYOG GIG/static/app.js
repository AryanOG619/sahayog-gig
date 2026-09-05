'use strict';

let selectedService = 'Home Cleaning';
let currentPrice = 299;
let selectedWorkerId = 1;
let activeBookingId = null;

// Initialize Date to today
document.getElementById('custDate').value = new Date().toISOString().split('T')[0];

function setRole(role) {
  document.querySelectorAll('.role-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.view-panel').forEach(v => v.classList.remove('active'));

  if (role === 'customer') {
    document.getElementById('btnRoleCustomer').classList.add('active');
    document.getElementById('viewCustomer').classList.add('active');
  } else if (role === 'worker') {
    document.getElementById('btnRoleWorker').classList.add('active');
    document.getElementById('viewWorker').classList.add('active');
    loadWorkerDashboard();
  } else if (role === 'admin') {
    document.getElementById('btnRoleAdmin').classList.add('active');
    document.getElementById('viewAdmin').classList.add('active');
    loadAdminLedger();
  }
}

function selectService(name, price) {
  selectedService = name;
  currentPrice = price;
  document.querySelectorAll('.service-pill').forEach(p => {
    p.classList.toggle('active', p.textContent.includes(name));
  });
  updateEscrowMath();
}

function updateEscrowMath() {
  const coop = Math.round(currentPrice * 0.04);
  const worker = currentPrice - coop;
  const total = currentPrice + coop;

  document.getElementById('priceBase').textContent = `₹${currentPrice}`;
  document.getElementById('priceCoop').textContent = `+ ₹${coop}`;
  document.getElementById('priceWorker').textContent = `₹${worker}`;
  document.getElementById('priceTotal').textContent = `₹${total}`;
}

async function loadWorkers() {
  try {
    const res = await fetch('/api/workers');
    const workers = await res.json();
    const c = document.getElementById('workersContainer');
    c.innerHTML = workers.map(w => `
      <div class="worker-pick-card ${w.id === selectedWorkerId ? 'selected' : ''}" onclick="selectWorker(${w.id})">
        <div class="worker-pick-avatar">👩‍🔧</div>
        <div>
          <strong>${w.name}</strong> · ⭐ ${w.rating}
          <div style="font-size:0.8rem; color:#10b981; font-weight:600;">📍 ${w.distance_km} km away · ${w.verification_badge}</div>
        </div>
      </div>
    `).join('');
  } catch (e) { console.error(e); }
}

function selectWorker(id) {
  selectedWorkerId = id;
  loadWorkers();
}

async function handleCustomerBooking(e) {
  e.preventDefault();
  const payload = {
    customer_name: document.getElementById('custName').value,
    customer_phone: document.getElementById('custPhone').value,
    address: document.getElementById('custAddress').value,
    service_name: selectedService,
    worker_id: selectedWorkerId,
    base_price: currentPrice,
    scheduled_date: document.getElementById('custDate').value,
    scheduled_slot: document.getElementById('custSlot').value
  };

  const btn = document.getElementById('btnSubmitBooking');
  btn.textContent = 'Locking in Escrow...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/bookings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    activeBookingId = data.booking_id;

    // Show Live Status
    document.getElementById('trackId').textContent = `#SG${data.booking_id}`;
    document.getElementById('trackStatusBadge').textContent = 'WAITING FOR WORKER ACCEPTANCE';
    document.getElementById('customerLiveTracker').classList.remove('hidden');
    btn.textContent = '✓ Escrow Locked & Dispatched';
  } catch (err) {
    alert('Booking error occurred');
  } finally {
    btn.disabled = false;
  }
}

async function loadWorkerDashboard() {
  try {
    const wRes = await fetch('/api/workers/1');
    const wData = await wRes.json();
    document.getElementById('workerNetEarnings').textContent = `₹${wData.total_earnings.toLocaleString()}`;
    document.getElementById('workerJobsCount').textContent = wData.completed_jobs;

    const bRes = await fetch('/api/bookings?worker_id=1');
    const bookings = await bRes.json();
    const alerts = document.getElementById('workerJobAlerts');

    if (bookings.length === 0) {
      alerts.innerHTML = `<p class="text-muted">No pending dispatches right now.</p>`;
      return;
    }

    alerts.innerHTML = bookings.map(b => `
      <div class="job-alert-item">
        <div>
          <strong>${b.service_name} (#SG${b.id})</strong>
          <p style="font-size:0.85rem; color:#64748b;">📍 ${b.address}</p>
          <div style="font-size:0.85rem; font-weight:700; color:#10b981;">Net Take-Home: ₹${b.worker_payout} (96% direct)</div>
          <small>Status: ${b.status}</small>
        </div>
        <div class="action-btns">
          ${b.status === 'PENDING_ACCEPTANCE' ? `<button class="btn-accept" onclick="updateBookingStatus(${b.id}, 'ACCEPTED')">Accept Task</button>` : ''}
          ${b.status === 'ACCEPTED' ? `<button class="btn-complete" onclick="updateBookingStatus(${b.id}, 'COMPLETED')">Mark Finished</button>` : ''}
          ${b.status === 'COMPLETED' ? `<span style="color:#10b981;font-weight:700">✓ Settled</span>` : ''}
        </div>
      </div>
    `).join('');
  } catch (e) { console.error(e); }
}

async function updateBookingStatus(id, newStatus) {
  await fetch(`/api/bookings/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus })
  });
  loadWorkerDashboard();
  if (activeBookingId === id) {
    document.getElementById('trackStatusBadge').textContent = newStatus;
  }
}

async function loadAdminLedger() {
  try {
    const res = await fetch('/api/bookings');
    const bookings = await res.json();
    const tbody = document.getElementById('adminLedgerBody');
    tbody.innerHTML = bookings.map(b => `
      <tr>
        <td>#SG${b.id}</td>
        <td>${b.service_name}</td>
        <td>${b.customer_name}</td>
        <td>₹${b.base_price + b.coop_fee}</td>
        <td style="color:#6d28d9;font-weight:700">₹${b.coop_fee}</td>
        <td style="color:#10b981;font-weight:700">₹${b.worker_payout}</td>
        <td><strong>${b.status}</strong></td>
      </tr>
    `).join('');
  } catch (e) { console.error(e); }
}

// Initial Boot
loadWorkers();
updateEscrowMath();