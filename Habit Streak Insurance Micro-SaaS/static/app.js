/**
 * Habit Streak Insurance - Frontend App
 */

const API_BASE = '';  // Same origin

// =============================================================================
// STATE
// =============================================================================

let currentUser = null;
let habits = [];
let antiCharities = [];
let habitCategories = [];
let habitToDelete = null;

// =============================================================================
// DOM ELEMENTS
// =============================================================================

const authSection = document.getElementById('auth-section');
const dashboardSection = document.getElementById('dashboard-section');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const tabBtns = document.querySelectorAll('.tab-btn');
const logoutBtn = document.getElementById('logout-btn');
const userEmailEl = document.getElementById('user-email');
const habitModal = document.getElementById('habit-modal');
const habitForm = document.getElementById('habit-form');
const addHabitBtn = document.getElementById('add-habit-btn');
const cancelHabitBtn = document.getElementById('cancel-habit-btn');
const habitsList = document.getElementById('habits-list');
const donationsList = document.getElementById('donations-list');
const antiCharitySelect = document.getElementById('habit-anti-charity');
const categorySelect = document.getElementById('habit-category');
const notificationSelect = document.getElementById('habit-notification');
const deleteModal = document.getElementById('delete-modal');
const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
const deleteModalMessage = document.getElementById('delete-modal-message');

// Stat elements
const statHabits = document.getElementById('stat-habits');
const statStreak = document.getElementById('stat-streak');
const statAtRisk = document.getElementById('stat-at-risk');
const statDonated = document.getElementById('stat-donated');

// =============================================================================
// API HELPERS
// =============================================================================

async function api(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        credentials: 'include',
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || 'Something went wrong');
    }

    return data;
}

// =============================================================================
// AUTH
// =============================================================================

async function checkAuth() {
    try {
        const data = await api('/api/auth/me');
        currentUser = data.user;
        showDashboard();
    } catch (e) {
        showAuth();
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');

    try {
        errorEl.textContent = '';
        const data = await api('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        currentUser = data.user;
        showDashboard();
    } catch (e) {
        errorEl.textContent = e.message;
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const errorEl = document.getElementById('register-error');

    try {
        errorEl.textContent = '';
        const data = await api('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
        currentUser = data.user;
        showDashboard();
    } catch (e) {
        errorEl.textContent = e.message;
    }
}

async function handleLogout() {
    await api('/api/auth/logout', { method: 'POST' });
    currentUser = null;
    showAuth();
}

function showAuth() {
    authSection.classList.remove('hidden');
    dashboardSection.classList.add('hidden');
}

function showDashboard() {
    authSection.classList.add('hidden');
    dashboardSection.classList.remove('hidden');
    userEmailEl.textContent = currentUser.email;
    loadDashboard();
    loadAntiCharities();
    loadHabitCategories();
}

// =============================================================================
// DASHBOARD
// =============================================================================

async function loadDashboard() {
    try {
        const data = await api('/api/dashboard');
        habits = data.habits;

        // Update stats
        statHabits.textContent = data.stats.total_habits;
        statStreak.textContent = data.stats.best_streak;
        statAtRisk.textContent = data.stats.money_at_risk_today.toFixed(2);
        statDonated.textContent = data.stats.total_donated.toFixed(2);

        renderHabits();
        loadDonations();
    } catch (e) {
        console.error('Failed to load dashboard:', e);
    }
}

async function loadDonations() {
    try {
        const data = await api('/api/donations');
        renderDonations(data.donations);
    } catch (e) {
        console.error('Failed to load donations:', e);
    }
}

async function loadAntiCharities() {
    try {
        const data = await api('/api/anti-charities');
        antiCharities = data.anti_charities;
        populateAntiCharitySelect();
    } catch (e) {
        console.error('Failed to load anti-charities:', e);
    }
}

async function loadHabitCategories() {
    try {
        const data = await api('/api/habit-categories');
        habitCategories = data.categories;
        populateCategorySelect();
    } catch (e) {
        console.error('Failed to load habit categories:', e);
    }
}

function populateCategorySelect() {
    categorySelect.innerHTML = '<option value="">Select a category...</option>';

    habitCategories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat.id;
        option.textContent = `${cat.icon} ${cat.name}`;
        option.title = cat.description;
        categorySelect.appendChild(option);
    });
}

function populateAntiCharitySelect() {
    antiCharitySelect.innerHTML = '<option value="">Select an organization you despise...</option>';

    // Group by category
    const categories = {};
    antiCharities.forEach(ac => {
        if (!categories[ac.category]) {
            categories[ac.category] = [];
        }
        categories[ac.category].push(ac);
    });

    Object.entries(categories).forEach(([category, orgs]) => {
        const group = document.createElement('optgroup');
        group.label = category.charAt(0).toUpperCase() + category.slice(1);

        orgs.forEach(org => {
            const option = document.createElement('option');
            option.value = org.id;
            option.textContent = org.name;
            option.title = org.description;
            group.appendChild(option);
        });

        antiCharitySelect.appendChild(group);
    });
}

// =============================================================================
// HABITS
// =============================================================================

function renderHabits() {
    if (habits.length === 0) {
        habitsList.innerHTML = `
            <div class="empty-state">
                <p>No habits yet. Time to put some skin in the game.</p>
                <button class="btn btn-primary" onclick="showHabitModal()">+ Create Your First Habit</button>
            </div>
        `;
        return;
    }

    habitsList.innerHTML = habits.map(habit => `
        <div class="habit-card" data-id="${habit.id}">
            <div class="habit-info">
                <div class="habit-header">
                    ${habit.category ? `<span class="category-badge" style="background: ${habit.category.color}20; color: ${habit.category.color}; border: 1px solid ${habit.category.color}40">${habit.category.icon} ${escapeHtml(habit.category.name)}</span>` : ''}
                </div>
                <div class="habit-name">${escapeHtml(habit.name)}</div>
                <div class="habit-meta">
                    <span>$${habit.weekly_stake.toFixed(2)}/week</span>
                    <span>${habit.anti_charity ? `Funds: ${escapeHtml(habit.anti_charity.name)}` : 'No anti-charity set'}</span>
                    <span>${getNotificationLabel(habit.notification_frequency)}</span>
                </div>
            </div>
            <div class="habit-actions">
                <div class="streak-badge ${habit.current_streak > 0 ? 'active' : ''}">
                    ${habit.current_streak} day streak
                </div>
                ${habit.checked_in_today
                    ? `<button class="btn btn-success checked-in" disabled>Checked In</button>`
                    : `<button class="btn btn-success" onclick="checkIn(${habit.id})">Check In</button>`
                }
                <button class="btn btn-danger" onclick="simulateMiss(${habit.id})" title="Simulate missing a day">
                    Simulate Miss
                </button>
                <button class="btn btn-danger btn-delete" onclick="showDeleteModal(${habit.id})" title="Delete habit">
                    Delete
                </button>
            </div>
        </div>
    `).join('');
}

function renderDonations(donations) {
    if (donations.length === 0) {
        donationsList.innerHTML = `
            <div class="empty-state">
                <p>No donations yet. Keep your streak alive!</p>
            </div>
        `;
        return;
    }

    donationsList.innerHTML = donations.map(donation => {
        const habit = habits.find(h => h.id === donation.habit_id);
        return `
            <div class="donation-card">
                <div class="donation-info">
                    <div class="donation-habit">${habit ? escapeHtml(habit.name) : 'Unknown habit'}</div>
                    <div class="donation-recipient">Donated to: ${donation.anti_charity ? escapeHtml(donation.anti_charity.name) : 'Unknown'}</div>
                    <div class="donation-date">Missed: ${new Date(donation.missed_date).toLocaleDateString()}</div>
                </div>
                <div class="donation-amount">$${donation.amount.toFixed(2)}</div>
            </div>
        `;
    }).join('');
}

async function checkIn(habitId) {
    try {
        const data = await api(`/api/habits/${habitId}/checkin`, { method: 'POST' });
        showNotification(`Checked in! Streak: ${data.streak} days`);
        loadDashboard();
    } catch (e) {
        showNotification(e.message, 'error');
    }
}

async function simulateMiss(habitId) {
    const habit = habits.find(h => h.id === habitId);
    if (!habit.anti_charity) {
        showNotification('Set an anti-charity first!', 'error');
        return;
    }

    if (!confirm(`This will simulate missing a day and donate $${(habit.weekly_stake / 7).toFixed(2)} to ${habit.anti_charity.name}. Continue?`)) {
        return;
    }

    try {
        const data = await api('/api/simulate-missed-day', {
            method: 'POST',
            body: JSON.stringify({ habit_id: habitId }),
        });
        showNotification(data.message, 'error');
        loadDashboard();
    } catch (e) {
        showNotification(e.message, 'error');
    }
}

// =============================================================================
// HABIT MODAL
// =============================================================================

function showHabitModal() {
    habitModal.classList.remove('hidden');
    document.getElementById('habit-name').focus();
}

function hideHabitModal() {
    habitModal.classList.add('hidden');
    habitForm.reset();
}

async function handleCreateHabit(e) {
    e.preventDefault();

    const name = document.getElementById('habit-name').value;
    const description = document.getElementById('habit-description').value;
    const categoryId = document.getElementById('habit-category').value;
    const weeklyStake = parseFloat(document.getElementById('habit-stake').value);
    const antiCharityId = document.getElementById('habit-anti-charity').value;
    const notificationFrequency = document.getElementById('habit-notification').value;

    try {
        await api('/api/habits', {
            method: 'POST',
            body: JSON.stringify({
                name,
                description,
                category_id: categoryId || null,
                weekly_stake: weeklyStake,
                anti_charity_id: antiCharityId || null,
                notification_frequency: notificationFrequency,
            }),
        });
        hideHabitModal();
        showNotification('Habit created! Now keep it up or pay the price.');
        loadDashboard();
    } catch (e) {
        showNotification(e.message, 'error');
    }
}

// =============================================================================
// UTILITIES
// =============================================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getNotificationLabel(frequency) {
    const labels = {
        'multiple_daily': 'Reminders: Multiple daily',
        'daily': 'Reminders: Daily',
        'weekly': 'Reminders: Weekly',
        'off': 'Reminders: Off'
    };
    return labels[frequency] || 'Reminders: Daily';
}

// =============================================================================
// DELETE CONFIRMATION MODAL
// =============================================================================

function showDeleteModal(habitId) {
    const habit = habits.find(h => h.id === habitId);
    if (!habit) return;

    habitToDelete = habitId;
    deleteModalMessage.textContent = `Are you sure you want to delete "${habit.name}"? This action cannot be undone.`;
    deleteModal.classList.remove('hidden');
}

function hideDeleteModal() {
    deleteModal.classList.add('hidden');
    habitToDelete = null;
}

async function handleDeleteHabit() {
    if (!habitToDelete) return;

    try {
        await api(`/api/habits/${habitToDelete}`, { method: 'DELETE' });
        hideDeleteModal();
        showNotification('Habit deleted successfully');
        loadDashboard();
    } catch (e) {
        showNotification(e.message, 'error');
    }
}

function showNotification(message, type = 'success') {
    // Simple notification - could be enhanced with a proper toast system
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'error' ? '#e53935' : '#43a047'};
        color: white;
        border-radius: 8px;
        font-weight: 500;
        z-index: 2000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add animation keyframes
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
`;
document.head.appendChild(style);

// =============================================================================
// EVENT LISTENERS
// =============================================================================

// Auth tabs
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const tab = btn.dataset.tab;
        if (tab === 'login') {
            loginForm.classList.remove('hidden');
            registerForm.classList.add('hidden');
        } else {
            loginForm.classList.add('hidden');
            registerForm.classList.remove('hidden');
        }
    });
});

// Auth forms
loginForm.addEventListener('submit', handleLogin);
registerForm.addEventListener('submit', handleRegister);
logoutBtn.addEventListener('click', handleLogout);

// Habit modal
addHabitBtn.addEventListener('click', showHabitModal);
cancelHabitBtn.addEventListener('click', hideHabitModal);
habitModal.addEventListener('click', (e) => {
    if (e.target === habitModal) hideHabitModal();
});
habitForm.addEventListener('submit', handleCreateHabit);

// Delete modal
confirmDeleteBtn.addEventListener('click', handleDeleteHabit);
cancelDeleteBtn.addEventListener('click', hideDeleteModal);
deleteModal.addEventListener('click', (e) => {
    if (e.target === deleteModal) hideDeleteModal();
});

// =============================================================================
// INIT
// =============================================================================

checkAuth();
