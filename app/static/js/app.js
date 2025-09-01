// Flask SaaS Starter - Main JavaScript Application

document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme toggle
    initThemeToggle();
    
    // Initialize tooltips
    initTooltips();
    
    // Initialize form validations
    initFormValidations();
    
    // Initialize HTMX event listeners
    initHTMXListeners();
});

// Theme Toggle Functionality
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const htmlElement = document.documentElement;
    
    // Get saved theme or default to light
    let currentTheme = localStorage.getItem('theme') || 'light';
    htmlElement.setAttribute('data-bs-theme', currentTheme);
    updateThemeIcon(currentTheme);
    
    themeToggle.addEventListener('click', function() {
        currentTheme = currentTheme === 'light' ? 'dark' : 'light';
        htmlElement.setAttribute('data-bs-theme', currentTheme);
        localStorage.setItem('theme', currentTheme);
        updateThemeIcon(currentTheme);
    });
    
    function updateThemeIcon(theme) {
        themeIcon.className = theme === 'light' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
    }
}

// Initialize Bootstrap tooltips
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Form Validation Enhancements
function initFormValidations() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Real-time validation for email fields
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            validateEmail(this);
        });
    });
    
    // Password strength indicator
    const passwordInputs = document.querySelectorAll('input[type="password"][name="password"]');
    passwordInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            updatePasswordStrength(this);
        });
    });
}

function validateEmail(input) {
    const email = input.value;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (email && !emailRegex.test(email)) {
        input.setCustomValidity('Please enter a valid email address');
        input.classList.add('is-invalid');
    } else {
        input.setCustomValidity('');
        input.classList.remove('is-invalid');
        if (email) input.classList.add('is-valid');
    }
}

function updatePasswordStrength(input) {
    const password = input.value;
    const strengthIndicator = document.getElementById('password-strength');
    
    if (!strengthIndicator) return;
    
    let strength = 0;
    let feedback = [];
    
    // Length check
    if (password.length >= 8) strength++;
    else feedback.push('At least 8 characters');
    
    // Uppercase check
    if (/[A-Z]/.test(password)) strength++;
    else feedback.push('One uppercase letter');
    
    // Lowercase check
    if (/[a-z]/.test(password)) strength++;
    else feedback.push('One lowercase letter');
    
    // Number check
    if (/\d/.test(password)) strength++;
    else feedback.push('One number');
    
    // Special character check
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength++;
    else feedback.push('One special character');
    
    const strengthLevels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
    const strengthColors = ['danger', 'warning', 'info', 'primary', 'success'];
    
    strengthIndicator.innerHTML = `
        <div class="progress mb-2" style="height: 8px;">
            <div class="progress-bar bg-${strengthColors[strength-1] || 'danger'}" 
                 role="progressbar" 
                 style="width: ${(strength/5)*100}%"></div>
        </div>
        <small class="text-${strengthColors[strength-1] || 'danger'}">
            ${strengthLevels[strength-1] || 'Very Weak'}
            ${feedback.length ? ' - Missing: ' + feedback.join(', ') : ''}
        </small>
    `;
}

// HTMX Event Listeners
function initHTMXListeners() {
    // Show loading state for HTMX requests
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        const target = evt.detail.target;
        if (target.classList.contains('htmx-indicator')) {
            target.style.opacity = '0.5';
        }
    });
    
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        const target = evt.detail.target;
        if (target.classList.contains('htmx-indicator')) {
            target.style.opacity = '1';
        }
    });
    
    // Handle HTMX errors
    document.body.addEventListener('htmx:responseError', function(evt) {
        showToast('An error occurred. Please try again.', 'error');
    });
}

// Utility Functions
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

// Confirmation dialogs
function confirmDelete(message = 'Are you sure you want to delete this item?') {
    return confirm(message);
}

// Data export functionality
function exportToCSV(data, filename = 'export.csv') {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function convertToCSV(data) {
    if (!data.length) return '';
    
    const headers = Object.keys(data[0]);
    const csvHeaders = headers.join(',');
    const csvRows = data.map(row => 
        headers.map(header => {
            const value = row[header];
            return typeof value === 'string' && value.includes(',') ? `"${value}"` : value;
        }).join(',')
    );
    
    return [csvHeaders, ...csvRows].join('\n');
}

// Auto-save functionality for forms
function initAutoSave(formSelector, saveUrl, interval = 30000) {
    const form = document.querySelector(formSelector);
    if (!form) return;
    
    let saveTimeout;
    
    form.addEventListener('input', function() {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => {
            autoSaveForm(form, saveUrl);
        }, interval);
    });
}

function autoSaveForm(form, saveUrl) {
    const formData = new FormData(form);
    
    fetch(saveUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Changes saved automatically', 'success');
        }
    })
    .catch(error => {
        console.error('Auto-save failed:', error);
    });
}

// Search functionality with debouncing
function initSearchWithDebounce(inputSelector, searchFunction, delay = 300) {
    const searchInput = document.querySelector(inputSelector);
    if (!searchInput) return;
    
    let searchTimeout;
    
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            searchFunction(this.value);
        }, delay);
    });
}

// Live search for user tables
function searchUsers(query) {
    const tableBody = document.querySelector('#users-table tbody');
    if (!tableBody) return;
    
    fetch(`/dashboard/users/search?q=${encodeURIComponent(query)}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        updateUsersTable(data.users);
    })
    .catch(error => {
        console.error('Search failed:', error);
    });
}

function updateUsersTable(users) {
    const tableBody = document.querySelector('#users-table tbody');
    if (!tableBody) return;
    
    tableBody.innerHTML = users.map(user => `
        <tr>
            <td>
                <div class="d-flex align-items-center">
                    <div class="avatar-sm bg-primary rounded-circle d-flex align-items-center justify-content-center text-white me-3">
                        ${user.first_name[0]}${user.last_name[0]}
                    </div>
                    <div>
                        <h6 class="mb-0">${user.full_name}</h6>
                        <small class="text-muted">${user.username}</small>
                    </div>
                </div>
            </td>
            <td>${user.email}</td>
            <td><span class="badge bg-${user.role === 'admin' ? 'danger' : user.role === 'manager' ? 'warning' : 'secondary'}">${user.role}</span></td>
            <td><span class="badge status-${user.is_active ? 'active' : 'inactive'}">${user.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>${new Date(user.created_at).toLocaleDateString()}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editUser(${user.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteUser(${user.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// User management functions
function editUser(userId) {
    // Open edit modal or redirect to edit page
    window.location.href = `/dashboard/users/${userId}/edit`;
}

function deleteUser(userId) {
    if (confirmDelete('Are you sure you want to delete this user?')) {
        fetch(`/api/v1/users/${userId}`, {
            method: 'DELETE',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('User deleted successfully', 'success');
                // Refresh the table
                location.reload();
            } else {
                showToast(data.message || 'Failed to delete user', 'error');
            }
        })
        .catch(error => {
            console.error('Delete failed:', error);
            showToast('An error occurred', 'error');
        });
    }
}

// File upload with progress
function initFileUpload() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                uploadFile(file, this);
            }
        });
    });
}

function uploadFile(file, input) {
    const formData = new FormData();
    formData.append('file', file);
    
    const progressBar = input.parentNode.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = '0%';
        progressBar.parentNode.style.display = 'block';
    }
    
    fetch('/api/v1/upload', {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('File uploaded successfully', 'success');
            if (progressBar) {
                progressBar.style.width = '100%';
                setTimeout(() => {
                    progressBar.parentNode.style.display = 'none';
                }, 1000);
            }
        } else {
            showToast(data.message || 'Upload failed', 'error');
        }
    })
    .catch(error => {
        console.error('Upload failed:', error);
        showToast('Upload failed', 'error');
    });
}

// Real-time notifications (WebSocket or SSE could be added here)
function initNotifications() {
    // Placeholder for real-time notification system
    // This could be expanded to use WebSockets or Server-Sent Events
}

// Dashboard chart initialization
function initDashboardCharts() {
    const chartElements = document.querySelectorAll('.chart-container');
    
    chartElements.forEach(element => {
        const chartType = element.dataset.chartType;
        const chartData = JSON.parse(element.dataset.chartData);
        
        switch(chartType) {
            case 'line':
                createLineChart(element, chartData);
                break;
            case 'bar':
                createBarChart(element, chartData);
                break;
            case 'doughnut':
                createDoughnutChart(element, chartData);
                break;
        }
    });
}

function createLineChart(element, data) {
    const ctx = element.querySelector('canvas').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Utility functions for API calls
async function apiCall(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    };
    
    const response = await fetch(url, { ...defaultOptions, ...options });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
}

// Copy to clipboard functionality
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('Copied to clipboard', 'success');
    }).catch(function(err) {
        console.error('Failed to copy: ', err);
        showToast('Failed to copy', 'error');
    });
}