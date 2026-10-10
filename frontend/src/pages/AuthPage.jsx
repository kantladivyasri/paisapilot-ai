import React, { useState } from 'react';
import {
  Lock,
  User,
  Mail,
  Eye,
  EyeOff,
  LogIn,
  UserPlus,
  ShieldCheck,
  Bot,
  Zap,
  Sparkles,
  TrendingUp,
  AlertCircle,
  Coins,
  ArrowRight,
} from 'lucide-react';
import { api, authStorage } from '../services/api';

export default function AuthPage({ onLoginSuccess }) {
  const [mode, setMode] = useState('login'); // 'login' or 'register'
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Form states
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [name, setName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSwitchMode = (newMode) => {
    setMode(newMode);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (mode === 'login') {
        if (!usernameOrEmail.trim() || !password) {
          throw new Error('Please enter your username or email and password.');
        }

        const res = await api.login({
          username_or_email: usernameOrEmail.trim(),
          password,
        });

        authStorage.setToken(res.access_token);
        authStorage.setUser(res.user);
        onLoginSuccess(res.user, `Welcome back, ${res.user.name || res.user.username}!`);
      } else {
        if (!username.trim() || !email.trim() || !password) {
          throw new Error('All fields are required to register.');
        }
        if (password.length < 6) {
          throw new Error('Password must be at least 6 characters long.');
        }

        const res = await api.register({
          username: username.trim().toLowerCase(),
          email: email.trim().toLowerCase(),
          password,
          name: name.trim() || username.trim(),
          currency: 'INR',
        });

        authStorage.setToken(res.access_token);
        authStorage.setUser(res.user);
        onLoginSuccess(res.user, `Account created successfully! Welcome, ${res.user.name || res.user.username}.`);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDemoLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      // Register or login a quick demo account
      const demoUsername = 'demo_pilot';
      const demoPassword = 'Password123';
      try {
        const res = await api.login({
          username_or_email: demoUsername,
          password: demoPassword,
        });
        authStorage.setToken(res.access_token);
        authStorage.setUser(res.user);
        onLoginSuccess(res.user, 'Logged into Demo Profile!');
      } catch {
        // If not registered yet, register it
        const res = await api.register({
          username: demoUsername,
          email: 'demo@nidhipilot.ai',
          password: demoPassword,
          name: 'Demo Pilot User',
          currency: 'INR',
        });
        authStorage.setToken(res.access_token);
        authStorage.setUser(res.user);
        // Automatically seed demo data for this profile
        try {
          await api.seedDemo(true);
        } catch {
          // ignore
        }
        onLoginSuccess(res.user, 'Demo account created and loaded!');
      }
    } catch (err) {
      setError(err.message || 'Failed to initialize demo login.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-navy-950 text-slate-100 flex flex-col justify-center items-center p-4 sm:p-6 lg:p-8 font-sans selection:bg-emerald-500 selection:text-navy-950">
      {/* Background ambient glow */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl"></div>
      </div>

      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        {/* Left Hero & Feature Highlights (Columns 1-7) */}
        <div className="lg:col-span-7 space-y-6 text-left">
          {/* Brand Header */}
          <div className="flex items-center gap-3.5">
            <div className="h-14 w-14 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-xl shadow-emerald-500/20 text-navy-950 font-black text-3xl">
              ₹
            </div>
            <div>
              <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight flex items-center gap-2">
                Nidhi Pilot <span className="text-emerald-400 text-sm px-2.5 py-0.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30">AI</span>
              </h1>
              <p className="text-sm text-slate-400 font-medium mt-0.5">
                Understand Your Money. Plan Your Future.
              </p>
            </div>
          </div>

          <div className="space-y-3 pt-2">
            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight leading-snug">
              Intelligent multi-tenant personal finance with <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-300">LangChain AI Agents</span>.
            </h2>
            <p className="text-sm text-slate-400 leading-relaxed max-w-xl">
              Sign in to enter your private personal workspace. All transactions, monthly salaries, custom categories, and AI conversations are securely isolated to your account.
            </p>
          </div>

          {/* Value Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-2">
            <div className="bg-navy-900/80 border border-slate-800 rounded-2xl p-4 flex items-start gap-3 shadow-sm">
              <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 shrink-0">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-200">Autonomous AI Copilot</h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  LangChain tool-calling agents for live balance & affordability queries.
                </p>
              </div>
            </div>

            <div className="bg-navy-900/80 border border-slate-800 rounded-2xl p-4 flex items-start gap-3 shadow-sm">
              <div className="p-2 rounded-xl bg-teal-500/10 text-teal-400 shrink-0">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-200">Smart Import Agent</h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Effortlessly parse bank SMS, UPI alerts, and statements into records.
                </p>
              </div>
            </div>

            <div className="bg-navy-900/80 border border-slate-800 rounded-2xl p-4 flex items-start gap-3 shadow-sm">
              <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 shrink-0">
                <TrendingUp className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-200">Predictive Forecasting</h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  50/30/20 budget planner and run-rate excessive spending warnings.
                </p>
              </div>
            </div>

            <div className="bg-navy-900/80 border border-slate-800 rounded-2xl p-4 flex items-start gap-3 shadow-sm">
              <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 shrink-0">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-200">Private Data Isolation</h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Multi-tenant encrypted credentials with bcrypt & JWT authentication.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Auth Card (Columns 8-12) */}
        <div className="lg:col-span-5 w-full">
          <div className="bg-navy-900/90 border border-slate-800 backdrop-blur-xl rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
            {/* Top Accent Line */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 to-teal-400"></div>

            {/* Tab Toggle */}
            <div className="flex bg-slate-950/70 p-1.5 rounded-2xl border border-slate-800/80 mb-6">
              <button
                type="button"
                onClick={() => handleSwitchMode('login')}
                className={`flex-1 py-2.5 text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition-all ${
                  mode === 'login'
                    ? 'bg-emerald-500 text-navy-950 shadow-md shadow-emerald-500/20'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <LogIn className="w-3.5 h-3.5" />
                Sign In
              </button>
              <button
                type="button"
                onClick={() => handleSwitchMode('register')}
                className={`flex-1 py-2.5 text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition-all ${
                  mode === 'register'
                    ? 'bg-emerald-500 text-navy-950 shadow-md shadow-emerald-500/20'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <UserPlus className="w-3.5 h-3.5" />
                Create Account
              </button>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-5 p-3.5 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-start gap-2.5 text-rose-300 text-xs text-left animate-in fade-in">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
                <span>{error}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4 text-left">
              {mode === 'register' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Your Full Name
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Arjun Sharma"
                      className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl pl-10 pr-3.5 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                    />
                    <User className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                  </div>
                </div>
              )}

              {mode === 'register' ? (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Choose Username
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      required
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="e.g. arjun_sharma"
                      className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl pl-10 pr-3.5 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                    />
                    <User className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Username or Email
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      required
                      value={usernameOrEmail}
                      onChange={(e) => setUsernameOrEmail(e.target.value)}
                      placeholder="Enter username or email"
                      className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl pl-10 pr-3.5 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                    />
                    <User className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                  </div>
                </div>
              )}

              {mode === 'register' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Email Address
                  </label>
                  <div className="relative">
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="e.g. arjun@example.com"
                      className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl pl-10 pr-3.5 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                    />
                    <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={mode === 'register' ? 'Minimum 6 characters' : 'Enter your password'}
                    className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl pl-10 pr-10 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                  />
                  <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-3.5" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-slate-400 hover:text-slate-200 absolute right-3.5 top-3.5 p-0.5"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-3.5 px-4 rounded-xl font-bold text-sm bg-emerald-500 hover:bg-emerald-400 text-navy-950 transition-all shadow-lg shadow-emerald-500/20 active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <span>Processing...</span>
                ) : mode === 'login' ? (
                  <>
                    <LogIn className="w-4 h-4" />
                    <span>Enter Dashboard</span>
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4" />
                    <span>Register & Open Dashboard</span>
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </>
                )}
              </button>
            </form>

            {/* Quick Demo Option */}
            <div className="mt-5 pt-4 border-t border-slate-800/80 text-center">
              <button
                type="button"
                onClick={handleQuickDemoLogin}
                disabled={loading}
                className="w-full py-2.5 px-3 text-xs font-semibold rounded-xl bg-teal-500/10 text-teal-300 border border-teal-500/30 hover:bg-teal-500/20 transition-all flex items-center justify-center gap-2"
              >
                <Sparkles className="w-3.5 h-3.5 text-teal-400" />
                <span>Instant Demo Login (1-Click Test)</span>
              </button>
              <p className="text-[11px] text-slate-500 mt-2">
                Evaluators & reviewers can click above to test immediately with demo data.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
