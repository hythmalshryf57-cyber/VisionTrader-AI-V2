// API helper with auth support
const api = {
  // Use Render backend URL or local for testing
  baseUrl: localStorage.getItem('api_base_url') || window.API_BASE_URL || window.API_URL || ((window.location.origin && window.location.origin !== 'null') ? window.location.origin : 'https://alphavision-backend.onrender.com'),
  async request(method, path, data = null, auth = true) {
    const url = path.startsWith('http') ? path : this.baseUrl + (path.startsWith('/') ? '' : '/') + path;
    const headers = {};
    if (data) headers['Content-Type'] = 'application/json';
    if (auth) {
      const t = localStorage.getItem('token');
      if (t) headers['Authorization'] = 'Bearer ' + t;
    }
    const res = await fetch(url, { method, headers, body: data ? JSON.stringify(data) : undefined });
    const txt = await res.text();
    let json;
    try { json = JSON.parse(txt); } catch { json = txt; }
    
    if (!res.ok) {
      const errorMsg = (json && json.detail) ? json.detail : 'حدث خطأ في الاتصال';
      throw new Error(errorMsg);
    }
    return json;
  },
  async login(email, password) { return this.request('POST', '/api/auth/login', { email, password }, false); },
  async register(email, password, invite_code) { return this.request('POST', '/api/auth/register', { email, password, invite_code: invite_code || '' }, false); },
  async requestInvite(email) { return this.request('POST', '/api/auth/request-invite', { email: email || '' }, false); },
  async validateInvite(invite_code) { return this.request('POST', '/api/auth/validate-invite', { invite_code }, true); },
  async me() { return this.request('GET', '/api/auth/me', null, true); },
  async calculateRisk(payload) { return this.request('POST', '/api/risk/calculate', payload, true); },
  
  // Scanner endpoints
  async getScannerStatus() { return this.request('GET', '/api/scanner/status', null, true); },
  async startScanner() { return this.request('POST', '/api/scanner/start', {}, true); },
  async stopScanner() { return this.request('POST', '/api/scanner/stop', {}, true); },
  async getAlerts() { return this.request('GET', '/api/scanner/alerts', null, true); },
  async getTopOpportunities() { return this.request('GET', '/api/scanner/top-opportunities', null, true); },

  // Analysis & Chat
  async analyzeMarket(market, images) { return this.request('POST', '/api/analysis/process', { market, images }, true); },
  // Auto analysis without uploading a chart — backend captures & analyzes 3 TFs.
  async autoAnalysis(market, trade_type) { return this.request('POST', '/api/analysis/auto', { market, trade_type }, true); },
  async getMentorResponse(query) { return this.request('POST', '/api/analysis/mentor', { query }, true); },
  async askAssistant(question) { return this.request('POST', '/api/ai/assistant', { question }, true); },
  async askAgent(formData) {
    const url = this.baseUrl + '/api/ai/agent';
    const token = localStorage.getItem('token');
    const headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const res = await fetch(url, { method: 'POST', headers, body: formData });
    const txt = await res.text();
    let json;
    try { json = JSON.parse(txt); } catch { json = txt; }
    if (!res.ok) {
      const errorMsg = (json && json.detail) ? json.detail : 'فشل الاتصال بالوكيل';
      throw new Error(errorMsg);
    }
    return json;
  },
  async getMarketSession() { return this.request('GET', '/api/market/session', null, true); },
  async getMarketSpread() { return this.request('GET', '/api/market/spread', null, true); },
  async getMarketPrice(symbol = 'BTCUSDT') { return this.request('GET', `/api/market/price?symbol=${encodeURIComponent(symbol)}`, null, false); },
  async detectChart(file) {
    const url = this.baseUrl + '/api/chart/detect';
    const token = localStorage.getItem('token');
    const headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(url, { method: 'POST', headers, body: form });
    const txt = await res.text();
    let json;
    try { json = JSON.parse(txt); } catch { json = txt; }
    if (!res.ok) {
      const errorMsg = (json && json.detail) ? json.detail : 'خطأ في تحليل الصورة';
      throw new Error(errorMsg);
    }
    return json;
  },

  // Journal & Stats
  async getJournal() { return this.request('GET', '/api/journal', null, true); },
  async addJournalEntry(entry) { return this.request('POST', '/api/journal', entry, true); },
  async getComparisonStats() { return this.request('GET', '/api/stats/comparison', null, true); },
  async getJournalInsights() { return this.request('GET', '/api/journal/insights', null, true); },
  async getUserPreferences() { return this.request('GET', '/api/user/preferences', null, true); },
  async updateUserPreferences(payload) { return this.request('POST', '/api/user/preferences', payload, true); },
  async getWatchlist() { return this.request('GET', '/api/user/watchlist', null, true); },
  async addWatchlistItem(symbol) { return this.request('POST', '/api/user/watchlist/add', { symbol }, true); },
  async removeWatchlistItem(symbol) { return this.request('POST', '/api/user/watchlist/remove', { symbol }, true); },
  async getFavorites() { return this.request('GET', '/api/user/favorites', null, true); },
  async addFavorite(strategy) { return this.request('POST', '/api/user/favorites', { strategy }, true); },
  async removeFavorite(strategy) { return this.request('POST', '/api/user/favorites/remove', { strategy }, true); },
  async saveAnalysisDraft(payload) { return this.request('POST', '/api/analysis/draft', payload, true); },
  async exportJournalCsv() {
    const url = this.baseUrl + '/api/journal/export';
    const headers = { 'Authorization': 'Bearer ' + localStorage.getItem('token') };
    const res = await fetch(url, { method: 'GET', headers });
    if (!res.ok) {
      const text = await res.text();
      let json;
      try { json = JSON.parse(text); } catch {};
      const errorMsg = (json && json.detail) ? json.detail : 'فشل تحميل CSV';
      throw new Error(errorMsg);
    }
    return await res.text();
  },
  async getDailyReports(days = 7) { return this.request('GET', `/api/reports/daily?days=${encodeURIComponent(days)}`, null, true); },
  async generateDailyReport() { return this.request('POST', '/api/reports/daily/generate', {}, true); },
  async sendDailyReportTelegram() { return this.request('POST', '/api/reports/daily/send-telegram', {}, true); },
  async getAccountSummary() { return this.request('GET', '/api/account/summary', null, true); },
  async getTodayStats() { return this.request('GET', '/api/stats/today', null, true); },
  async getPerformanceStats() { return this.request('GET', '/api/stats/performance', null, true); },
  async getScannerStats() { return this.request('GET', '/api/stats/scanner', null, true); },
  async getSystemStrategies() { return this.request('GET', '/api/system/strategies', null, true); },
  async getTradeMoverRecommendation(analysisId, currentPrice = null) {
    let query = `/api/trade-mover/check?analysis_id=${encodeURIComponent(analysisId)}`;
    if (currentPrice !== null && currentPrice !== undefined) {
      query += `&current_price=${encodeURIComponent(currentPrice)}`;
    }
    return this.request('GET', query, null, true);
  },

  // Deep Market Scanner
  async getDeepMarketScan(symbol = 'XAUUSDT') {
    return this.request('GET', `/api/deep-market/scan?symbol=${encodeURIComponent(symbol)}`, null, true);
  },
  async scanBinance(symbol = 'BTCUSDT') {
    return this.request('GET', `/api/binance/scan?symbol=${encodeURIComponent(symbol)}`, null, true);
  },
  async fetchTradingView(url) {
    return this.request('POST', '/api/tradingview/fetch', { url }, true);
  },
  async getCalendarEvents(hours = 24) {
    return this.request('GET', `/api/calendar/events?hours=${encodeURIComponent(hours)}`, null, true);
  },
  async getHighImpactEvents(minutes = 15) {
    return this.request('GET', `/api/calendar/high-impact?minutes=${encodeURIComponent(minutes)}`, null, true);
  },
  async getSystemHealth() { return this.request('GET', '/api/admin/system-health', null, true); },
  applyTheme() {
    const stored = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', stored);
    document.body.dataset.theme = stored;
    const toggle = document.querySelectorAll('[data-theme-toggle]');
    toggle.forEach(el => el.innerText = stored === 'light' ? '🌙' : '☀️');
  },
  toggleTheme() {
    const current = localStorage.getItem('theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    this.applyTheme();
    return next;
  },
  applyLanguage() {
    const stored = localStorage.getItem('language') || 'ar';
    document.documentElement.lang = stored;
    document.documentElement.dir = stored === 'ar' ? 'rtl' : 'ltr';
    const labels = this.translations[stored] || {};
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.dataset.i18n;
      if (labels[key]) el.innerText = labels[key];
    });
    const langToggle = document.querySelectorAll('[data-lang-toggle]');
    langToggle.forEach(el => el.innerText = stored === 'ar' ? 'EN' : 'العربية');
    const select = document.getElementById('langSelect');
    if (select) select.value = stored;
  },
  toggleLanguage() {
    const current = localStorage.getItem('language') || 'ar';
    const next = current === 'ar' ? 'en' : 'ar';
    localStorage.setItem('language', next);
    this.applyLanguage();
    return next;
  },
  translations: {
    ar: {
      welcome_title: 'مرحباً، متداول Alpha',
      welcome_subtitle: 'آخر تحليلاتك كانت على الذهب (XAUUSD) بنسبة ثقة 92%.',
      dark_mode: 'الوضع الداكن',
      language: 'اللغة',
      watchlist_title: 'قائمة المراقبة',
      add_watchlist: 'إضافة رمز جديد',
      daily_report_title: 'التقرير اليومي',
      send_telegram: 'إرسال للتليجرام',
      dashboard_summary: 'ملخص اليوم',
      watchlist_empty: 'لا توجد أسواق مفضلة بعد. أضف أول رمز.'
    },
    en: {
      welcome_title: 'Welcome, Alpha Trader',
      welcome_subtitle: 'Your last analysis was on Gold (XAUUSD) with 92% confidence.',
      dark_mode: 'Dark Mode',
      language: 'Language',
      watchlist_title: 'Watchlist',
      add_watchlist: 'Add new symbol',
      daily_report_title: 'Daily Report',
      send_telegram: 'Send to Telegram',
      dashboard_summary: 'Today Summary',
      watchlist_empty: 'No favorite markets yet. Add your first symbol.'
    }
  }
};

window.api = api;

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const prefs = await api.getUserPreferences();
    if (prefs.theme) localStorage.setItem('theme', prefs.theme);
    if (prefs.language) localStorage.setItem('language', prefs.language);
  } catch (err) {
    // User may not be logged in yet; local settings still apply
  }
  api.applyTheme();
  api.applyLanguage();
});
