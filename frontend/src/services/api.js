const API_BASE = '/api';

export const authStorage = {
  getToken: () => localStorage.getItem('nidhi_auth_token') || '',
  setToken: (token) => {
    if (token) localStorage.setItem('nidhi_auth_token', token);
    else localStorage.removeItem('nidhi_auth_token');
  },
  getUser: () => {
    try {
      const data = localStorage.getItem('nidhi_user_profile');
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },
  setUser: (user) => {
    if (user) localStorage.setItem('nidhi_user_profile', JSON.stringify(user));
    else localStorage.removeItem('nidhi_user_profile');
  },
  clear: () => {
    localStorage.removeItem('nidhi_auth_token');
    localStorage.removeItem('nidhi_user_profile');
  },
};

function authHeaders(customHeaders = {}) {
  const token = authStorage.getToken();
  const headers = { ...customHeaders };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse(res) {
  // Read response stream text exactly once
  const rawText = await res.text();
  let parsed = null;
  try {
    parsed = rawText ? JSON.parse(rawText) : null;
  } catch {
    // rawText is HTML, plain text, or empty
  }

  if (!res.ok) {
    let errorDetail = '';
    if (parsed && parsed.detail) {
      if (Array.isArray(parsed.detail)) {
        errorDetail = parsed.detail.map((e) => e.msg || JSON.stringify(e)).join('; ');
      } else if (typeof parsed.detail === 'object' && parsed.detail !== null) {
        errorDetail = JSON.stringify(parsed.detail);
      } else {
        errorDetail = String(parsed.detail);
      }
    } else if (parsed && parsed.message) {
      errorDetail = String(parsed.message);
    } else if (res.status === 502 || res.status === 504 || res.status === 503) {
      errorDetail = 'Backend server is not reachable. Please ensure the backend server is running on port 8000.';
    } else if (rawText && rawText.trim().length > 0 && rawText.trim().length < 300) {
      errorDetail = rawText.trim();
    } else {
      errorDetail = `Request failed with status ${res.status} (${res.statusText || 'Error'})`;
    }
    throw new Error(errorDetail);
  }

  return parsed !== null ? parsed : rawText;
}

export const api = {
  // Authentication & Profile
  register: (data) =>
    fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  login: (data) =>
    fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  getMe: () =>
    fetch(`${API_BASE}/auth/me`, {
      headers: authHeaders(),
    }).then(handleResponse),

  updateProfile: (data) =>
    fetch(`${API_BASE}/auth/profile`, {
      method: 'PUT',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  // Health
  getHealth: () => fetch(`${API_BASE}/health`).then(handleResponse),

  // Monthly Salary Management
  getSalary: (month) =>
    fetch(`${API_BASE}/salary${month ? `?month=${month}` : ''}`, {
      headers: authHeaders(),
    }).then(handleResponse),

  setSalary: (data) =>
    fetch(`${API_BASE}/salary`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  getSalaries: () =>
    fetch(`${API_BASE}/salaries`, {
      headers: authHeaders(),
    }).then(handleResponse),

  // Dynamic Categories Management
  getCategories: (month) =>
    fetch(`${API_BASE}/categories${month ? `?month=${month}` : ''}`, {
      headers: authHeaders(),
    }).then(handleResponse),

  createCategory: (data) =>
    fetch(`${API_BASE}/categories`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  updateCategory: (id, data) =>
    fetch(`${API_BASE}/categories/${id}`, {
      method: 'PUT',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteCategory: (id) =>
    fetch(`${API_BASE}/categories/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    }).then(handleResponse),

  // Period Tracking (Daily, Weekly, Monthly, Yearly, Custom)
  getPeriodReport: (periodType = 'monthly', params = {}) => {
    const query = new URLSearchParams();
    query.append('period_type', periodType);
    if (params.reference_date) query.append('reference_date', params.reference_date);
    if (params.target_date) query.append('target_date', params.target_date);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    return fetch(`${API_BASE}/reports/period?${query.toString()}`, {
      headers: authHeaders(),
    }).then(handleResponse);
  },

  // Transactions (with Filtering, Pagination, Sorting, Payment Method)
  getTransactions: (params = {}) => {
    const query = new URLSearchParams();
    if (params.category && params.category !== 'All') query.append('category', params.category);
    if (params.transaction_type && params.transaction_type !== 'all') query.append('transaction_type', params.transaction_type);
    if (params.payment_method && params.payment_method !== 'all') query.append('payment_method', params.payment_method);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.search) query.append('search', params.search);
    if (params.page !== undefined) query.append('page', params.page);
    if (params.page_size !== undefined) query.append('page_size', params.page_size);
    if (params.sort_by) query.append('sort_by', params.sort_by);
    if (params.sort_order) query.append('sort_order', params.sort_order);
    const qs = query.toString();
    return fetch(`${API_BASE}/transactions${qs ? `?${qs}` : ''}`, {
      headers: authHeaders(),
    }).then(handleResponse);
  },

  createTransaction: (data) =>
    fetch(`${API_BASE}/transactions`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  updateTransaction: (id, data) =>
    fetch(`${API_BASE}/transactions/${id}`, {
      method: 'PUT',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteTransaction: (id) =>
    fetch(`${API_BASE}/transactions/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    }).then(handleResponse),

  importCsv: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/transactions/import`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    }).then(handleResponse);
  },

  // Analytics & Summary
  getSummary: (month) =>
    fetch(`${API_BASE}/summary${month ? `?month=${month}` : ''}`, {
      headers: authHeaders(),
    }).then(handleResponse),

  getAnalysis: (month) =>
    fetch(`${API_BASE}/analysis${month ? `?month=${month}` : ''}`, {
      headers: authHeaders(),
    }).then(handleResponse),

  getForecast: (month) =>
    fetch(`${API_BASE}/analysis/forecast${month ? `?month=${month}` : ''}`, {
      headers: authHeaders(),
    }).then(handleResponse),

  // Budget
  getBudget: (month) =>
    fetch(`${API_BASE}/budget${month ? `?month=${month}` : ''}`, {
      headers: authHeaders(),
    }).then(handleResponse),

  saveBudget: (data) =>
    fetch(`${API_BASE}/budget`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  generateBudget: (data) =>
    fetch(`${API_BASE}/budget/generate`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  // Savings Goals
  getGoals: () =>
    fetch(`${API_BASE}/goals`, {
      headers: authHeaders(),
    }).then(handleResponse),

  createGoal: (data) =>
    fetch(`${API_BASE}/goals`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  updateGoal: (id, data) =>
    fetch(`${API_BASE}/goals/${id}`, {
      method: 'PUT',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteGoal: (id) =>
    fetch(`${API_BASE}/goals/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    }).then(handleResponse),

  // AI Chat & History
  sendChatMessage: (message, context_month = null) =>
    fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ message, context_month }),
    }).then(handleResponse),

  getChatHistory: () =>
    fetch(`${API_BASE}/chat/history`, {
      headers: authHeaders(),
    }).then(handleResponse),

  clearChatHistory: () =>
    fetch(`${API_BASE}/chat/history`, {
      method: 'DELETE',
      headers: authHeaders(),
    }).then(handleResponse),

  // Settings & Keys
  getSettings: () => fetch(`${API_BASE}/settings`).then(handleResponse),

  updateSettings: (data) =>
    fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  // Demo Data
  seedDemo: (force = true) =>
    fetch(`${API_BASE}/demo/seed?force=${force}`, {
      method: 'POST',
      headers: authHeaders(),
    }).then(handleResponse),

  resetDemo: () =>
    fetch(`${API_BASE}/demo/reset`, {
      method: 'POST',
      headers: authHeaders(),
    }).then(handleResponse),

  // Automated Transaction Import Agent
  previewImportAgent: (text, sourceType = 'auto') =>
    fetch(`${API_BASE}/agents/import-transactions/preview`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ text, source_type: sourceType }),
    }).then(handleResponse),

  commitImportAgent: (transactions, skipDuplicates = true) =>
    fetch(`${API_BASE}/agents/import-transactions/commit?skip_duplicates=${skipDuplicates}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ transactions }),
    }).then(handleResponse),

  autoImportAgent: (text) =>
    fetch(`${API_BASE}/agents/import-transactions/auto`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ text }),
    }).then(handleResponse),

  // Recurring & Common Monthly Expenses (Bills, EMIs, Insurance)
  getRecurringExpenses: () =>
    fetch(`${API_BASE}/recurring-expenses`, {
      headers: authHeaders(),
    }).then(handleResponse),

  createRecurringExpense: (data) =>
    fetch(`${API_BASE}/recurring-expenses`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  updateRecurringExpense: (id, data) =>
    fetch(`${API_BASE}/recurring-expenses/${id}`, {
      method: 'PUT',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteRecurringExpense: (id) =>
    fetch(`${API_BASE}/recurring-expenses/${id}`, {
      method: 'DELETE',
      headers: authHeaders(),
    }).then(handleResponse),

  logRecurringTransaction: (id) =>
    fetch(`${API_BASE}/recurring-expenses/${id}/log-transaction`, {
      method: 'POST',
      headers: authHeaders(),
    }).then(handleResponse),

  // Mobile Alerts & Budget Overrun Warnings
  getAlertStatus: () =>
    fetch(`${API_BASE}/alerts/status`, {
      headers: authHeaders(),
    }).then(handleResponse),

  checkAndNotifyAlerts: (force = false) =>
    fetch(`${API_BASE}/alerts/check-and-notify?force=${force}`, {
      method: 'POST',
      headers: authHeaders(),
    }).then(handleResponse),

  sendTestSms: (phoneNumber = null) =>
    fetch(`${API_BASE}/alerts/send-test`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(phoneNumber ? { phone_number: phoneNumber } : {}),
    }).then(handleResponse),

  getAlertLogs: (limit = 20) =>
    fetch(`${API_BASE}/alerts/logs?limit=${limit}`, {
      headers: authHeaders(),
    }).then(handleResponse),

  getGatewayConfig: () =>
    fetch(`${API_BASE}/alerts/gateway-config`, {
      headers: authHeaders(),
    }).then(handleResponse),

  updateGatewayConfig: (data) =>
    fetch(`${API_BASE}/alerts/gateway-config`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  // Email Alert Methods
  sendTestEmail: (email = null) =>
    fetch(`${API_BASE}/alerts/send-test-email`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(email ? { email } : {}),
    }).then(handleResponse),

  getEmailGatewayConfig: () =>
    fetch(`${API_BASE}/alerts/email-config`, {
      headers: authHeaders(),
    }).then(handleResponse),

  updateEmailGatewayConfig: (data) =>
    fetch(`${API_BASE}/alerts/email-config`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(data),
    }).then(handleResponse),

  getEmailAlertLogs: (limit = 20) =>
    fetch(`${API_BASE}/alerts/email-logs?limit=${limit}`, {
      headers: authHeaders(),
    }).then(handleResponse),
};


