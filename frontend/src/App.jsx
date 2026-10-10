import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Navbar from './components/Navbar';
import TransactionModal from './components/TransactionModal';
import CsvImportModal from './components/CsvImportModal';
import SmartImportModal from './components/SmartImportModal';
import SettingsModal from './components/SettingsModal';
import ConfirmModal from './components/ConfirmModal';
import AuthModal from './components/AuthModal';
import ProfileModal from './components/ProfileModal';
import AuthPage from './pages/AuthPage';

import Dashboard from './pages/Dashboard';
import TransactionsPage from './pages/TransactionsPage';
import AnalysisPage from './pages/AnalysisPage';
import BudgetPage from './pages/BudgetPage';
import GoalsPage from './pages/GoalsPage';
import ChatPage from './pages/ChatPage';

import { api, authStorage } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [currentUser, setCurrentUser] = useState(() => authStorage.getUser());
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState(null);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isSmartImportOpen, setIsSmartImportOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [isResetConfirmOpen, setIsResetConfirmOpen] = useState(false);
  const [groqConfigured, setGroqConfigured] = useState(false);
  const [loadingAction, setLoadingAction] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Key to force refresh child pages after seed/reset/import/auth switch
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    checkHealthAndSettings();
    verifyAuthSession();
  }, []);

  const showToast = (msg, type = 'success') => {
    setToastMessage({ text: msg, type });
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  const checkHealthAndSettings = async () => {
    try {
      const data = await api.getHealth();
      setGroqConfigured(Boolean(data.groq_configured));
    } catch {
      // ignore
    }
  };

  const verifyAuthSession = async () => {
    const token = authStorage.getToken();
    if (!token) return;

    try {
      const profile = await api.getMe();
      authStorage.setUser(profile);
      setCurrentUser(profile);
    } catch {
      // If token expired or invalid, clear stored session
      authStorage.clear();
      setCurrentUser(null);
    }
  };

  const handleAuthSuccess = (user, message) => {
    setCurrentUser(user);
    showToast(message || `Welcome, ${user.name || user.username}!`);
    setRefreshKey((k) => k + 1);
  };

  const handleLogout = () => {
    authStorage.clear();
    setCurrentUser(null);
    setActiveTab('dashboard');
    showToast('Signed out successfully. Please sign in to access your dashboard.');
    setRefreshKey((k) => k + 1);
  };

  const handleSaveTransaction = async (data) => {
    if (editingTransaction) {
      await api.updateTransaction(editingTransaction.id, data);
      showToast('Transaction successfully updated!');
    } else {
      await api.createTransaction(data);
      showToast('Transaction successfully recorded!');
    }
    setRefreshKey((k) => k + 1);
  };

  const handleImportCsv = async (file) => {
    const res = await api.importCsv(file);
    showToast(`CSV Imported: ${res.imported_count} transactions added!`);
    setRefreshKey((k) => k + 1);
    return res;
  };

  const handleSeedDemo = async () => {
    setLoadingAction(true);
    try {
      const res = await api.seedDemo(true);
      showToast(res.message || 'Fictional ₹30,000 demo profile loaded!');
      setRefreshKey((k) => k + 1);
    } catch (err) {
      showToast(`Seed failed: ${err.message}`, 'error');
    } finally {
      setLoadingAction(false);
    }
  };

  const handleResetConfirm = async () => {
    setLoadingAction(true);
    try {
      await api.resetDemo();
      setIsResetConfirmOpen(false);
      showToast('All transaction records have been reset.');
      setRefreshKey((k) => k + 1);
    } catch (err) {
      showToast(`Reset failed: ${err.message}`, 'error');
    } finally {
      setLoadingAction(false);
    }
  };

  // If user is not authenticated, render dedicated Auth Page
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-navy-950 text-slate-100 font-sans">
        {toastMessage && (
          <div className="fixed top-5 right-6 z-50 animate-in fade-in slide-in-from-top-2">
            <div
              className={`px-4 py-2.5 rounded-xl shadow-xl border text-xs font-semibold flex items-center gap-2 ${
                toastMessage.type === 'error'
                  ? 'bg-rose-500/90 text-white border-rose-400'
                  : 'bg-emerald-500/90 text-navy-950 border-emerald-400'
              }`}
            >
              <span>{toastMessage.text}</span>
            </div>
          </div>
        )}
        <AuthPage onLoginSuccess={handleAuthSuccess} />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-navy-950 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenSettings={() => setIsSettingsModalOpen(true)}
        groqConfigured={groqConfigured}
        onLogout={handleLogout}
      />

      {/* Main App Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar
          activeTab={activeTab}
          refreshKey={refreshKey}
          currentUser={currentUser}
          onOpenAuthModal={() => setIsAuthModalOpen(true)}
          onOpenProfileModal={() => setIsProfileModalOpen(true)}
          onLogout={handleLogout}
          onQuickAdd={() => {
            setEditingTransaction(null);
            setIsAddModalOpen(true);
          }}
          onOpenSmartImport={() => setIsSmartImportOpen(true)}
          onSeedDemo={handleSeedDemo}
          onResetDemo={() => setIsResetConfirmOpen(true)}
          onOpenSettings={() => setIsSettingsModalOpen(true)}
          loading={loadingAction}
        />

        {/* Dynamic Page Router */}
        <main className="flex-1 overflow-y-auto">
          {toastMessage && (
            <div className="fixed top-5 right-6 z-50 animate-in fade-in slide-in-from-top-2">
              <div
                className={`px-4 py-2.5 rounded-xl shadow-xl border text-xs font-semibold flex items-center gap-2 ${
                  toastMessage.type === 'error'
                    ? 'bg-rose-500/90 text-white border-rose-400'
                    : 'bg-emerald-500/90 text-navy-950 border-emerald-400'
                }`}
              >
                <span>{toastMessage.text}</span>
              </div>
            </div>
          )}

          {activeTab === 'dashboard' && (
            <Dashboard
              key={refreshKey}
              onNavigate={setActiveTab}
              onQuickAdd={() => {
                setEditingTransaction(null);
                setIsAddModalOpen(true);
              }}
              onOpenImport={() => setIsImportModalOpen(true)}
              onOpenSmartImport={() => setIsSmartImportOpen(true)}
            />
          )}

          {activeTab === 'transactions' && (
            <TransactionsPage
              key={refreshKey}
              onOpenAddModal={() => {
                setEditingTransaction(null);
                setIsAddModalOpen(true);
              }}
              onEditTransaction={(txn) => {
                setEditingTransaction(txn);
                setIsAddModalOpen(true);
              }}
              onOpenImport={() => setIsImportModalOpen(true)}
              onOpenSmartImport={() => setIsSmartImportOpen(true)}
              onClearAll={() => setIsResetConfirmOpen(true)}
            />
          )}

          {activeTab === 'analysis' && <AnalysisPage key={refreshKey} />}

          {activeTab === 'budget' && <BudgetPage key={refreshKey} />}

          {activeTab === 'goals' && <GoalsPage key={refreshKey} />}

          {activeTab === 'chat' && <ChatPage key={refreshKey} />}
        </main>
      </div>

      {/* Modals */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={handleAuthSuccess}
      />

      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        currentUser={currentUser}
        onProfileUpdated={(updated) => {
          setCurrentUser(updated);
          showToast('Profile updated successfully!');
          setRefreshKey((k) => k + 1);
        }}
        onLogout={handleLogout}
      />

      <TransactionModal
        isOpen={isAddModalOpen}
        onClose={() => {
          setIsAddModalOpen(false);
          setEditingTransaction(null);
        }}
        onSave={handleSaveTransaction}
        transaction={editingTransaction}
      />

      <CsvImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onImportSuccess={handleImportCsv}
      />

      <SmartImportModal
        isOpen={isSmartImportOpen}
        onClose={() => setIsSmartImportOpen(false)}
        onImportSuccess={(res) => {
          showToast(`Import Agent: ${res.imported_count} transaction(s) recorded!`);
          setRefreshKey((k) => k + 1);
        }}
      />

      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        onSettingsUpdated={checkHealthAndSettings}
      />

      <ConfirmModal
        isOpen={isResetConfirmOpen}
        title="Reset All Financial Data?"
        message="This will permanently clear all transactions, budgets, and savings goals from your local SQLite database."
        confirmText="Confirm Reset"
        confirmType="danger"
        loading={loadingAction}
        onConfirm={handleResetConfirm}
        onClose={() => setIsResetConfirmOpen(false)}
      />
    </div>
  );
}
