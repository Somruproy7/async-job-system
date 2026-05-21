// Configuration
const API_BASE_URL = 'https://async-job-system-production.up.railway.app/api/v1';

// State
let currentUser = null;
let accessToken = null;
let refreshToken = null;
let jobsRefreshInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

// Check if user is already logged in
function checkAuth() {
    accessToken = localStorage.getItem('accessToken');
    refreshToken = localStorage.getItem('refreshToken');
    
    if (accessToken) {
        fetchCurrentUser();
    } else {
        showPage('loginPage');
    }
}

// Setup Event Listeners
function setupEventListeners() {
    // Login
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('showRegister').addEventListener('click', (e) => {
        e.preventDefault();
        showPage('registerPage');
    });
    
    // Register
    document.getElementById('registerForm').addEventListener('submit', handleRegister);
    document.getElementById('showLogin').addEventListener('click', (e) => {
        e.preventDefault();
        showPage('loginPage');
    });
    
    // Dashboard
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    document.getElementById('refreshBtn').addEventListener('click', loadJobs);
    document.getElementById('createJobBtn').addEventListener('click', () => {
        document.getElementById('createJobModal').classList.add('active');
    });
    
    // Modals
    document.getElementById('closeCreateModal').addEventListener('click', () => {
        document.getElementById('createJobModal').classList.remove('active');
    });
    document.getElementById('cancelCreateJob').addEventListener('click', () => {
        document.getElementById('createJobModal').classList.remove('active');
    });
    document.getElementById('closeDetailsModal').addEventListener('click', () => {
        document.getElementById('jobDetailsModal').classList.remove('active');
    });
    
    // Create Job Form
    document.getElementById('createJobForm').addEventListener('submit', handleCreateJob);
    
    // Job Type - Update payload template
    document.getElementById('jobType').addEventListener('change', updatePayloadTemplate);
}

// Page Navigation
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');
}

// API Helpers
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (accessToken && !options.skipAuth) {
        headers['Authorization'] = `Bearer ${accessToken}`;
    }
    
    try {
        const response = await fetch(url, {
            ...options,
            headers
        });
        
        if (response.status === 401 && refreshToken && !options.skipAuth) {
            // Try to refresh token
            const refreshed = await refreshAccessToken();
            if (refreshed) {
                // Retry original request
                headers['Authorization'] = `Bearer ${accessToken}`;
                const retryResponse = await fetch(url, { ...options, headers });
                return await handleResponse(retryResponse);
            } else {
                handleLogout();
                return null;
            }
        }
        
        return await handleResponse(response);
    } catch (error) {
        console.error('API Error:', error);
        showError('networkError', 'Network error. Please check your connection.');
        return null;
    }
}

async function handleResponse(response) {
    let data = null;
    try {
        data = await response.json();
    } catch (e) {
        // Response has no JSON body
    }
    
    if (!response.ok) {
        let errorMessage;
        if (Array.isArray(data?.detail)) {
            // FastAPI validation errors: [{loc, msg, type}, ...]
            errorMessage = data.detail.map(e => e.msg).join('; ');
        } else {
            errorMessage = data?.detail || data?.message || `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
    }
    
    return data;
}

async function refreshAccessToken() {
    try {
        const data = await apiRequest('/auth/refresh', {
            method: 'POST',
            body: JSON.stringify({ refresh_token: refreshToken }),
            skipAuth: true
        });
        
        if (data && data.access_token) {
            accessToken = data.access_token;
            localStorage.setItem('accessToken', accessToken);
            return true;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
    }
    return false;
}

// Auth Functions
async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    showLoading('loginBtnText', 'loginSpinner');
    hideError('loginError');
    
    try {
        const data = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
            skipAuth: true
        });
        
        if (data) {
            accessToken = data.access_token;
            refreshToken = data.refresh_token;
            localStorage.setItem('accessToken', accessToken);
            localStorage.setItem('refreshToken', refreshToken);
            
            await fetchCurrentUser();
        }
    } catch (error) {
        showError('loginError', error.message);
    } finally {
        hideLoading('loginBtnText', 'loginSpinner');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    
    const email = document.getElementById('regEmail').value;
    const username = document.getElementById('regUsername').value;
    const password = document.getElementById('regPassword').value;
    
    // Validate username format
    const usernameRegex = /^[a-zA-Z0-9_-]+$/;
    if (!usernameRegex.test(username)) {
        showError('registerError', 'Username can only contain letters, numbers, underscore, and hyphen');
        return;
    }
    
    showLoading('registerBtnText', 'registerSpinner');
    hideError('registerError');
    hideError('registerSuccess');
    
    try {
        const data = await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, username, password }),
            skipAuth: true
        });
        
        if (data) {
            showSuccess('registerSuccess', 'Account created! Redirecting to login...');
            setTimeout(() => {
                showPage('loginPage');
                document.getElementById('email').value = email;
            }, 2000);
        }
    } catch (error) {
        showError('registerError', error.message);
    } finally {
        hideLoading('registerBtnText', 'registerSpinner');
    }
}

async function fetchCurrentUser() {
    try {
        const data = await apiRequest('/auth/me');
        
        if (data) {
            currentUser = data;
            showDashboard();
        }
    } catch (error) {
        console.error('Failed to fetch user:', error);
        handleLogout();
    }
}

function handleLogout() {
    accessToken = null;
    refreshToken = null;
    currentUser = null;
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    
    if (jobsRefreshInterval) {
        clearInterval(jobsRefreshInterval);
    }
    
    showPage('loginPage');
}

// Dashboard Functions
function showDashboard() {
    showPage('dashboardPage');
    
    // Update user info
    const userInfoEl = document.getElementById('userInfo');
    if (userInfoEl && currentUser) {
        const roleEmoji = currentUser.role === 'admin' ? '👑' : '👤';
        userInfoEl.textContent = `${roleEmoji} ${currentUser.username} (${currentUser.role})`;
    }
    
    // Load jobs
    loadJobs();
    
    // Auto-refresh every 5 seconds
    if (jobsRefreshInterval) {
        clearInterval(jobsRefreshInterval);
    }
    jobsRefreshInterval = setInterval(loadJobs, 5000);
}

async function loadJobs() {
    try {
        const data = await apiRequest('/jobs/?page=1&page_size=100');
        
        if (data) {
            updateStats(data.items);
            renderJobsTable(data.items);
        }
    } catch (error) {
        console.error('Failed to load jobs:', error);
    }
}

function updateStats(jobs) {
    const stats = {
        total: jobs.length,
        success: jobs.filter(j => j.status === 'success').length,
        running: jobs.filter(j => j.status === 'running').length,
        failed: jobs.filter(j => j.status === 'failed').length
    };
    
    const totalEl = document.getElementById('totalJobs');
    const successEl = document.getElementById('successJobs');
    const runningEl = document.getElementById('runningJobs');
    const failedEl = document.getElementById('failedJobs');
    
    if (totalEl) totalEl.textContent = stats.total;
    if (successEl) successEl.textContent = stats.success;
    if (runningEl) runningEl.textContent = stats.running;
    if (failedEl) failedEl.textContent = stats.failed;
}

function renderJobsTable(jobs) {
    const tbody = document.getElementById('jobsTableBody');
    
    if (jobs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px; color: var(--text-light);">
                    No jobs found. Create your first job!
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = jobs.map(job => `
        <tr>
            <td><strong>${escapeHtml(job.name)}</strong></td>
            <td>${formatJobType(job.job_type)}</td>
            <td><span class="status-badge status-${job.status}">${job.status}</span></td>
            <td>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${job.progress}%"></div>
                </div>
                <small>${job.progress.toFixed(0)}%</small>
            </td>
            <td><span class="priority-badge priority-${job.priority}">${job.priority}</span></td>
            <td>${formatDate(job.created_at)}</td>
            <td>
                <button class="action-btn btn-view" onclick="viewJobDetails('${job.id}')">View</button>
                ${job.status === 'pending' || job.status === 'queued' ? 
                    `<button class="action-btn btn-cancel" onclick="cancelJob('${job.id}')">Cancel</button>` : ''}
                ${job.status === 'failed' ? 
                    `<button class="action-btn btn-retry" onclick="retryJob('${job.id}')">Retry</button>` : ''}
            </td>
        </tr>
    `).join('');
}

// Job Actions
async function viewJobDetails(jobId) {
    const modal = document.getElementById('jobDetailsModal');
    const content = document.getElementById('jobDetailsContent');
    
    modal.classList.add('active');
    content.innerHTML = '<div class="spinner"></div> Loading...';
    
    try {
        const job = await apiRequest(`/jobs/${jobId}`);
        
        if (job) {
            content.innerHTML = `
                <div class="detail-row">
                    <div class="detail-label">Job ID</div>
                    <div class="detail-value"><code>${job.id}</code></div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Name</div>
                    <div class="detail-value">${escapeHtml(job.name)}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Type</div>
                    <div class="detail-value">${formatJobType(job.job_type)}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Status</div>
                    <div class="detail-value"><span class="status-badge status-${job.status}">${job.status}</span></div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Progress</div>
                    <div class="detail-value">${job.progress.toFixed(1)}%</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Priority</div>
                    <div class="detail-value"><span class="priority-badge priority-${job.priority}">${job.priority}</span></div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Status Message</div>
                    <div class="detail-value">${job.status_message || 'N/A'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Created</div>
                    <div class="detail-value">${formatDate(job.created_at)}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Started</div>
                    <div class="detail-value">${job.started_at ? formatDate(job.started_at) : 'N/A'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Completed</div>
                    <div class="detail-value">${job.completed_at ? formatDate(job.completed_at) : 'N/A'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Duration</div>
                    <div class="detail-value">${job.duration_seconds ? job.duration_seconds.toFixed(2) + 's' : 'N/A'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Retry Count</div>
                    <div class="detail-value">${job.retry_count} / ${job.max_retries}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Payload</div>
                    <div class="detail-value"><pre>${JSON.stringify(job.payload, null, 2)}</pre></div>
                </div>
                ${job.result ? `
                <div class="detail-row">
                    <div class="detail-label">Result</div>
                    <div class="detail-value"><pre>${JSON.stringify(job.result, null, 2)}</pre></div>
                </div>
                ` : ''}
                ${job.error_detail ? `
                <div class="detail-row">
                    <div class="detail-label">Error</div>
                    <div class="detail-value" style="color: var(--danger);">${escapeHtml(job.error_detail)}</div>
                </div>
                ` : ''}
            `;
        }
    } catch (error) {
        content.innerHTML = `<p style="color: var(--danger);">Failed to load job details: ${error.message}</p>`;
    }
}

async function cancelJob(jobId) {
    if (!confirm('Are you sure you want to cancel this job?')) return;
    
    try {
        await apiRequest(`/jobs/${jobId}/cancel`, { method: 'POST' });
        loadJobs();
    } catch (error) {
        alert('Failed to cancel job: ' + error.message);
    }
}

async function retryJob(jobId) {
    try {
        await apiRequest(`/jobs/${jobId}/retry`, { method: 'POST' });
        loadJobs();
    } catch (error) {
        alert('Failed to retry job: ' + error.message);
    }
}

// Create Job
function updatePayloadTemplate() {
    const jobType = document.getElementById('jobType').value;
    const payloadField = document.getElementById('jobPayload');
    
    const templates = {
        image_processing: {
            image_url: 'https://example.com/image.jpg',
            width: 800,
            format: 'webp'
        },
        report_generation: {
            report_type: 'sales',
            date_range: '2024-01-01 to 2024-12-31',
            filters: {}
        },
        email_sending: {
            recipients: ['user1@example.com', 'user2@example.com'],
            template_id: 'welcome',
            subject: 'Welcome!'
        },
        data_export: {
            query: 'SELECT * FROM users',
            format: 'csv',
            destination: 's3://bucket/export.csv'
        }
    };
    
    payloadField.value = JSON.stringify(templates[jobType] || {}, null, 2);
}

async function handleCreateJob(e) {
    e.preventDefault();
    
    const name = document.getElementById('jobName').value;
    const jobType = document.getElementById('jobType').value;
    const priority = document.getElementById('jobPriority').value;
    const payloadText = document.getElementById('jobPayload').value;
    
    let payload;
    try {
        payload = JSON.parse(payloadText);
    } catch (error) {
        alert('Invalid JSON in payload field');
        return;
    }
    
    try {
        await apiRequest('/jobs/', {
            method: 'POST',
            body: JSON.stringify({
                name,
                job_type: jobType,
                priority,
                payload
            })
        });
        
        document.getElementById('createJobModal').classList.remove('active');
        document.getElementById('createJobForm').reset();
        loadJobs();
    } catch (error) {
        alert('Failed to create job: ' + error.message);
    }
}

// Utility Functions
function showLoading(textId, spinnerId) {
    const textEl = document.getElementById(textId);
    const spinnerEl = document.getElementById(spinnerId);
    if (textEl) textEl.classList.add('hidden');
    if (spinnerEl) spinnerEl.classList.remove('hidden');
}

function hideLoading(textId, spinnerId) {
    const textEl = document.getElementById(textId);
    const spinnerEl = document.getElementById(spinnerId);
    if (textEl) textEl.classList.remove('hidden');
    if (spinnerEl) spinnerEl.classList.add('hidden');
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.classList.remove('hidden');
    }
}

function hideError(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.add('hidden');
    }
}

function showSuccess(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.classList.remove('hidden');
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function formatJobType(type) {
    return type.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
