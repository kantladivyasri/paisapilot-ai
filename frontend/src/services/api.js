const API_BASE = '/api';

async function handleResponse(res) {
  if (!res.ok) {
    let errorDetail = 'An unexpected error occurred';
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorJson.message || errorDetail;
    } catch {
      errorDetail = await res.text();
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Health
  getHealth: () => fetch(`${API_BASE}/health`).then(handleResponse),

  // Monthly Salary Management
  getSalary: (month) =>
    fetch(`${API_BASE}/salary${month ? `?month=${month}` : ''}`).then(handleResponse),

  setSalary: (data) =>
    fetch(`${API_BASE}/salary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  getSalaries: () =>
    fetch(`${API_BASE}/salaries`).then(handleResponse),

  // Dynamic Categories Management
  getCategories: (month) =>
    fetch(`${API_BASE}/categories${month ? `?month=${month}` : ''}`).then(handleResponse),

  createCategory: (data) =>
    fetch(`${API_BASE}/categories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  updateCategory: (id, data) =>
    fetch(`${API_BASE}/categories/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteCategory: (id) =>
    fetch(`${API_BASE}/categories/${id}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // Period Tracking (Daily, Weekly, Monthly, Yearly, Custom)
  getPeriodReport: (periodType = 'monthly', params = {}) => {
    const query = new URLSearchParams();
    query.append('period_type', periodType);
    if (params.reference_date) query.append('reference_date', params.reference_date);
    if (params.target_date) query.append('target_date', params.target_date);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    return fetch(`${API_BASE}/reports/period?${query.toString()}`).then(handleResponse);
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
    return fetch(`${API_BASE}/transactions${qs ? `?${qs}` : ''}`).then(handleResponse);
  },

  createTransaction: (data) =>
    fetch(`${API_BASE}/transactions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  updateTransaction: (id, data) =>
    fetch(`${API_BASE}/transactions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteTransaction: (id) =>
    fetch(`${API_BASE}/transactions/${id}`, {
      method: 'DELETE',
    }).then(handleResponse),

  importCsv: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${API_BASE}/transactions/import`, {
      method: 'POST',
      body: formData,
    }).then(handleResponse);
  },

  // Analytics & Summary
  getSummary: (month) =>
    fetch(`${API_BASE}/summary${month ? `?month=${month}` : ''}`).then(handleResponse),

  getAnalysis: (month) =>
    fetch(`${API_BASE}/analysis${month ? `?month=${month}` : ''}`).then(handleResponse),

  getForecast: (month) =>
    fetch(`${API_BASE}/analysis/forecast${month ? `?month=${month}` : ''}`).then(handleResponse),

  // Budget
  getBudget: (month) =>
    fetch(`${API_BASE}/budget${month ? `?month=${month}` : ''}`).then(handleResponse),

  saveBudget: (data) =>
    fetch(`${API_BASE}/budget`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  generateBudget: (data) =>
    fetch(`${API_BASE}/budget/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  // Savings Goals
  getGoals: () => fetch(`${API_BASE}/goals`).then(handleResponse),

  createGoal: (data) =>
    fetch(`${API_BASE}/goals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  updateGoal: (id, data) =>
    fetch(`${API_BASE}/goals/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  deleteGoal: (id) =>
    fetch(`${API_BASE}/goals/${id}`, {
      method: 'DELETE',
    }).then(handleResponse),

  // AI Chat & History
  sendChatMessage: (message, context_month = null) =>
    fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, context_month }),
    }).then(handleResponse),

  getChatHistory: () =>
    fetch(`${API_BASE}/chat/history`).then(handleResponse),

  clearChatHistory: () =>
    fetch(`${API_BASE}/chat/history`, {
      method: 'DELETE',
    }).then(handleResponse),

  // Settings & Keys
  getSettings: () => fetch(`${API_BASE}/settings`).then(handleResponse),

  updateSettings: (data) =>
    fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(handleResponse),

  // Demo Data
  seedDemo: (force = true) =>
    fetch(`${API_BASE}/demo/seed?force=${force}`, {
      method: 'POST',
    }).then(handleResponse),

  resetDemo: () =>
    fetch(`${API_BASE}/demo/reset`, {
      method: 'POST',
    }).then(handleResponse),
};
