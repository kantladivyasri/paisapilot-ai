import React, { useState, useEffect } from 'react';
import {
  X,
  User,
  Mail,
  Phone,
  Smartphone,
  Send,
  Lock,
  Eye,
  EyeOff,
  LogOut,
  Save,
  CheckCircle2,
  AlertCircle,
  Calendar,
  ShieldCheck,
  Coins,
  Radio,
  Settings2,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Key,
  Inbox,
  AtSign,
} from 'lucide-react';
import { api, authStorage } from '../services/api';

export default function ProfileModal({
  isOpen,
  onClose,
  currentUser,
  onProfileUpdated,
  onLogout,
}) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [currency, setCurrency] = useState('INR');
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  // SMS Gateway Configuration States
  const [gatewayInfo, setGatewayInfo] = useState(null);
  const [smsConfigOpen, setSmsConfigOpen] = useState(false);
  const [gatewayProvider, setGatewayProvider] = useState('fast2sms');
  const [fast2smsKey, setFast2smsKey] = useState('');
  const [twilioSid, setTwilioSid] = useState('');
  const [twilioToken, setTwilioToken] = useState('');
  const [twilioFrom, setTwilioFrom] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [savingGateway, setSavingGateway] = useState(false);
  const [gatewayNotice, setGatewayNotice] = useState(null);
  const [gatewayError, setGatewayError] = useState(null);

  // Email Alert & SMTP Gateway States
  const [emailGatewayInfo, setEmailGatewayInfo] = useState(null);
  const [emailConfigOpen, setEmailConfigOpen] = useState(false);
  const [smtpPreset, setSmtpPreset] = useState('gmail');
  const [smtpHost, setSmtpHost] = useState('smtp.gmail.com');
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpUser, setSmtpUser] = useState('');
  const [smtpPassword, setSmtpPassword] = useState('');
  const [showSmtpPassword, setShowSmtpPassword] = useState(false);
  const [savingEmailGateway, setSavingEmailGateway] = useState(false);
  const [emailGatewayNotice, setEmailGatewayNotice] = useState(null);
  const [emailGatewayError, setEmailGatewayError] = useState(null);
  const [testEmailLoading, setTestEmailLoading] = useState(false);
  const [testEmailNotice, setTestEmailNotice] = useState(null);
  const [emailLogs, setEmailLogs] = useState([]);
  const [previewEmail, setPreviewEmail] = useState(null);

  const [loading, setLoading] = useState(false);
  const [testSmsLoading, setTestSmsLoading] = useState(false);
  const [testSmsNotice, setTestSmsNotice] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const loadGatewayConfig = async () => {
    try {
      const config = await api.getGatewayConfig();
      setGatewayInfo(config);
      if (config.active_provider === 'Twilio') {
        setGatewayProvider('twilio');
      } else if (config.active_provider === 'Fast2SMS') {
        setGatewayProvider('fast2sms');
      }
    } catch (e) {
      console.warn('Could not load SMS gateway config:', e);
    }

    try {
      const eConfig = await api.getEmailGatewayConfig();
      setEmailGatewayInfo(eConfig);
      if (eConfig.smtp_host) {
        setSmtpHost(eConfig.smtp_host);
        setSmtpPort(eConfig.smtp_port);
        setSmtpUser(eConfig.smtp_user || currentUser?.email || '');
        if (eConfig.smtp_host.includes('gmail')) setSmtpPreset('gmail');
        else if (eConfig.smtp_host.includes('office365') || eConfig.smtp_host.includes('outlook')) setSmtpPreset('outlook');
        else setSmtpPreset('custom');
      } else {
        setSmtpUser(currentUser?.email || '');
      }
    } catch (e) {
      console.warn('Could not load email gateway config:', e);
    }

    try {
      const logs = await api.getEmailAlertLogs(5);
      setEmailLogs(logs || []);
    } catch (e) {
      console.warn('Could not load email logs:', e);
    }
  };

  const handleSelectSmtpPreset = (preset) => {
    setSmtpPreset(preset);
    if (preset === 'gmail') {
      setSmtpHost('smtp.gmail.com');
      setSmtpPort(587);
    } else if (preset === 'outlook') {
      setSmtpHost('smtp.office365.com');
      setSmtpPort(587);
    }
  };

  useEffect(() => {
    if (currentUser) {
      setName(currentUser.name || '');
      setEmail(currentUser.email || '');
      setPhoneNumber(currentUser.phone_number || '');
      setCurrency(currentUser.currency || 'INR');
      setError(null);
      setSuccess(null);
      setTestSmsNotice(null);
      setTestEmailNotice(null);
      setGatewayNotice(null);
      setGatewayError(null);
      setEmailGatewayNotice(null);
      setEmailGatewayError(null);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setChangePasswordOpen(false);
      loadGatewayConfig();
    }
  }, [currentUser, isOpen]);

  if (!isOpen || !currentUser) return null;

  const handleSaveEmailGateway = async () => {
    setEmailGatewayError(null);
    setEmailGatewayNotice(null);
    setSavingEmailGateway(true);
    try {
      const payload = {
        smtp_host: smtpHost.trim(),
        smtp_port: parseInt(smtpPort, 10) || 587,
        smtp_user: smtpUser.trim(),
        smtp_password: smtpPassword.trim(),
        smtp_from: smtpUser.trim(),
        smtp_tls: true,
      };
      const res = await api.updateEmailGatewayConfig(payload);
      setEmailGatewayInfo(res);
      setEmailGatewayNotice(res.message || 'Email Gateway (SMTP) credentials saved successfully!');
      setSmtpPassword('');
    } catch (err) {
      setEmailGatewayError(err.message || 'Failed to save email gateway credentials.');
    } finally {
      setSavingEmailGateway(false);
    }
  };

  const handleSendTestEmail = async () => {
    if (!email.trim()) {
      setError('Please provide an email address first to test email alerts.');
      return;
    }
    setTestEmailLoading(true);
    setTestEmailNotice(null);
    setError(null);
    try {
      const res = await api.sendTestEmail(email.trim());
      setTestEmailNotice(res.message || `Test alert email dispatched to ${email.trim()}!`);
      try {
        const logs = await api.getEmailAlertLogs(5);
        setEmailLogs(logs || []);
      } catch (_) {}
    } catch (err) {
      setError(err.message || 'Failed to dispatch test email.');
      if (err.message && (err.message.toLowerCase().includes('not configured') || err.message.toLowerCase().includes('smtp') || err.message.toLowerCase().includes('email gateway'))) {
        setEmailConfigOpen(true);
      }
    } finally {
      setTestEmailLoading(false);
    }
  };


  const handleSaveGateway = async () => {
    setGatewayError(null);
    setGatewayNotice(null);
    setSavingGateway(true);
    try {
      const payload = {
        provider: gatewayProvider,
        fast2sms_api_key: gatewayProvider === 'fast2sms' ? fast2smsKey.trim() : undefined,
        twilio_account_sid: gatewayProvider === 'twilio' ? twilioSid.trim() : undefined,
        twilio_auth_token: gatewayProvider === 'twilio' ? twilioToken.trim() : undefined,
        twilio_phone_number: gatewayProvider === 'twilio' ? twilioFrom.trim() : undefined,
      };
      const res = await api.updateGatewayConfig(payload);
      setGatewayInfo(res);
      setGatewayNotice(res.message || 'SMS Gateway credentials saved successfully!');
      setFast2smsKey('');
      setTwilioToken('');
    } catch (err) {
      setGatewayError(err.message || 'Failed to save SMS gateway credentials.');
    } finally {
      setSavingGateway(false);
    }
  };

  const handleSendTestSms = async () => {
    if (!phoneNumber.trim()) {
      setError('Please enter a phone number first to test SMS alerts.');
      return;
    }
    setTestSmsLoading(true);
    setTestSmsNotice(null);
    setError(null);
    try {
      const res = await api.sendTestSms(phoneNumber.trim());
      setTestSmsNotice(res.message || `Test alert sent to ${phoneNumber.trim()}!`);
    } catch (err) {
      setError(err.message || 'Failed to dispatch test SMS.');
      if (err.message && (err.message.toLowerCase().includes('not configured') || err.message.toLowerCase().includes('gateway'))) {
        setSmsConfigOpen(true);
      }
    } finally {
      setTestSmsLoading(false);
    }
  };


  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!name.trim()) {
      setError('Please provide your name.');
      return;
    }

    if (changePasswordOpen && newPassword) {
      if (newPassword.length < 6) {
        setError('New password must be at least 6 characters long.');
        return;
      }
      if (newPassword !== confirmPassword) {
        setError('New password and confirm password do not match.');
        return;
      }
      if (!currentPassword) {
        setError('Please enter your current password to set a new password.');
        return;
      }
    }

    setLoading(true);
    try {
      const payload = {
        name: name.trim(),
        email: email.trim() || undefined,
        phone_number: phoneNumber.trim() || undefined,
        currency: currency || 'INR',
      };

      if (changePasswordOpen && newPassword) {
        payload.current_password = currentPassword;
        payload.new_password = newPassword;
      }

      const updatedUser = await api.updateProfile(payload);
      authStorage.setUser(updatedUser);
      onProfileUpdated(updatedUser);

      setSuccess('Profile updated successfully!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setChangePasswordOpen(false);
    } catch (err) {
      setError(err.message || 'Failed to update profile.');
    } finally {
      setLoading(false);
    }
  };

  const formattedDate = currentUser.created_at
    ? new Date(currentUser.created_at).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : 'Member';

  const avatarInitial = (currentUser.name || currentUser.username || 'U')
    .charAt(0)
    .toUpperCase();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-navy-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-navy-950 font-black text-xl shadow-lg shadow-emerald-500/20">
              {avatarInitial}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-bold text-white tracking-tight">
                  {currentUser.name || currentUser.username}
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Active
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                @{currentUser.username || 'user'} • ID: {currentUser.id}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Form Body */}
        <form onSubmit={handleSaveProfile} className="p-6 overflow-y-auto space-y-4 flex-1">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl flex items-start gap-2.5 text-rose-300 text-xs animate-in fade-in">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center gap-2.5 text-emerald-300 text-xs animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              <span>{success}</span>
            </div>
          )}

          {/* Account Details Box */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 flex items-center justify-between text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-emerald-400" />
              <span>Joined: <strong className="text-slate-200">{formattedDate}</strong></span>
            </div>
            <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
              <ShieldCheck className="w-4 h-4" />
              <span>Multi-Tenant Isolated</span>
            </div>
          </div>

          {/* Full Name */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Full Name
            </label>
            <div className="relative">
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your full name"
                className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-10 pr-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
              />
              <User className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
            </div>
          </div>

          {/* Email Address */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-emerald-400" />
                <span>Email Address</span>
              </label>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Email Alerts Active
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your.email@example.com"
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-10 pr-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                />
                <AtSign className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              </div>
              <button
                type="button"
                onClick={handleSendTestEmail}
                disabled={testEmailLoading || !email.trim()}
                title="Send test budget alert email to verify delivery"
                className="px-3 py-2.5 text-xs font-semibold rounded-xl bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20 transition-all disabled:opacity-40 flex items-center gap-1.5 shrink-0"
              >
                <Send className="w-3 h-3" />
                <span>{testEmailLoading ? 'Sending...' : 'Test Email'}</span>
              </button>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Warning alerts, budget breaches, and financial health reports will be sent to this email.
            </p>
            {testEmailNotice && (
              <div className="mt-2 p-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-300 text-[11px] flex items-center gap-1.5 animate-in fade-in">
                <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                <span>{testEmailNotice}</span>
              </div>
            )}
          </div>


          {/* Mobile Phone Number */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-emerald-400" />
                <span>Mobile Phone Number</span>
              </label>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                SMS Alerts
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="+91 98765 43210"
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-10 pr-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                />
                <Smartphone className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              </div>
              <button
                type="button"
                onClick={handleSendTestSms}
                disabled={testSmsLoading || !phoneNumber.trim()}
                title="Send test budget alert SMS to verify delivery"
                className="px-3 py-2.5 text-xs font-semibold rounded-xl bg-teal-500/10 text-teal-300 border border-teal-500/30 hover:bg-teal-500/20 transition-all disabled:opacity-40 flex items-center gap-1.5 shrink-0"
              >
                <Send className="w-3 h-3" />
                <span>{testSmsLoading ? 'Sending...' : 'Test SMS'}</span>
              </button>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Warning alerts and over-budget SMS notifications will be dispatched to this mobile number.
            </p>
            {testSmsNotice && (
              <div className="mt-2 p-2 bg-teal-500/10 border border-teal-500/30 rounded-lg text-teal-300 text-[11px] flex items-center gap-1.5 animate-in fade-in">
                <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-teal-400" />
                <span>{testSmsNotice}</span>
              </div>
            )}
          </div>

          {/* Real SMS Gateway Setup Box */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-emerald-400 shrink-0" />
                <div>
                  <div className="text-xs font-semibold text-white flex items-center gap-2">
                    <span>Telecom SMS Gateway</span>
                    {gatewayInfo?.is_configured ? (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Active: {gatewayInfo.active_provider}
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        Unconfigured
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Required to route real SMS to mobile networks.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSmsConfigOpen(!smsConfigOpen)}
                className="text-xs font-medium text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition-colors px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20"
              >
                <Settings2 className="w-3.5 h-3.5" />
                <span>{smsConfigOpen ? 'Hide' : 'Configure'}</span>
                {smsConfigOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>

            {smsConfigOpen && (
              <div className="pt-3 border-t border-slate-800 space-y-3 animate-in fade-in">
                {gatewayNotice && (
                  <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    <span>{gatewayNotice}</span>
                  </div>
                )}
                {gatewayError && (
                  <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
                    <span>{gatewayError}</span>
                  </div>
                )}

                {/* Provider Selector Tabs */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1.5">
                    Select SMS Gateway Provider
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setGatewayProvider('fast2sms')}
                      className={`px-3 py-2 rounded-xl text-xs font-semibold border flex items-center justify-center gap-1.5 transition-all ${
                        gatewayProvider === 'fast2sms'
                          ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-300 shadow-sm'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <span>⚡ Fast2SMS (India)</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setGatewayProvider('twilio')}
                      className={`px-3 py-2 rounded-xl text-xs font-semibold border flex items-center justify-center gap-1.5 transition-all ${
                        gatewayProvider === 'twilio'
                          ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-300 shadow-sm'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <span>🌐 Twilio (Global)</span>
                    </button>
                  </div>
                </div>

                {/* Fast2SMS Fields */}
                {gatewayProvider === 'fast2sms' && (
                  <div className="space-y-2.5 bg-slate-950/60 border border-slate-800/80 p-3 rounded-xl">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-200">Fast2SMS Authorization Key</span>
                      <a
                        href="https://www.fast2sms.com"
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] text-emerald-400 hover:underline flex items-center gap-1"
                      >
                        Get Free Key <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <div className="relative">
                      <input
                        type={showApiKey ? 'text' : 'password'}
                        value={fast2smsKey}
                        onChange={(e) => setFast2smsKey(e.target.value)}
                        placeholder={gatewayInfo?.fast2sms_masked ? `Current: ${gatewayInfo.fast2sms_masked}` : 'Paste Fast2SMS API Key'}
                        className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-9 pr-10 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                      <Key className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
                      <button
                        type="button"
                        onClick={() => setShowApiKey(!showApiKey)}
                        className="text-slate-500 hover:text-slate-300 absolute right-3 top-2.5"
                      >
                        {showApiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                    <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5 text-[11px] text-slate-300 space-y-1">
                      <div className="font-semibold text-emerald-400 text-[11px]">⚡ 1-Minute Free Setup:</div>
                      <div>1. Open <a href="https://www.fast2sms.com" target="_blank" rel="noreferrer" className="text-teal-300 underline font-medium">fast2sms.com</a> & Sign Up (₹50 free credits, no card needed).</div>
                      <div>2. In left sidebar, click <strong className="text-white">Dev API</strong> and copy your <strong className="text-white">Authorization Key</strong>.</div>
                      <div>3. Paste the key above and click <strong className="text-white">Save Gateway Credentials</strong>.</div>
                    </div>

                  </div>
                )}

                {/* Twilio Fields */}
                {gatewayProvider === 'twilio' && (
                  <div className="space-y-2.5 bg-slate-950/60 border border-slate-800/80 p-3 rounded-xl">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-200">Twilio API Credentials</span>
                      <a
                        href="https://www.twilio.com"
                        target="_blank"
                        rel="noreferrer"
                        className="text-[11px] text-emerald-400 hover:underline flex items-center gap-1"
                      >
                        Twilio Console <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-1">Account SID</label>
                      <input
                        type="text"
                        value={twilioSid}
                        onChange={(e) => setTwilioSid(e.target.value)}
                        placeholder={gatewayInfo?.twilio_sid_masked ? `Current: ${gatewayInfo.twilio_sid_masked}` : 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}
                        className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-1">Auth Token</label>
                      <div className="relative">
                        <input
                          type={showApiKey ? 'text' : 'password'}
                          value={twilioToken}
                          onChange={(e) => setTwilioToken(e.target.value)}
                          placeholder="Twilio Auth Token"
                          className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 pr-10 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                        />
                        <button
                          type="button"
                          onClick={() => setShowApiKey(!showApiKey)}
                          className="text-slate-500 hover:text-slate-300 absolute right-3 top-2"
                        >
                          {showApiKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-1">Twilio Phone Number (From)</label>
                      <input
                        type="text"
                        value={twilioFrom}
                        onChange={(e) => setTwilioFrom(e.target.value)}
                        placeholder={gatewayInfo?.twilio_from || '+1234567890'}
                        className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                    <p className="text-[10px] text-slate-400">
                      For Twilio trial accounts, ensure recipient phone number is added to your verified caller list.
                    </p>
                  </div>
                )}

                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    onClick={handleSaveGateway}
                    disabled={savingGateway || (gatewayProvider === 'fast2sms' && !fast2smsKey.trim() && !gatewayInfo?.fast2sms_configured) || (gatewayProvider === 'twilio' && (!twilioSid.trim() || !twilioToken.trim() || !twilioFrom.trim()) && !gatewayInfo?.twilio_configured)}
                    className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors disabled:opacity-40 flex items-center gap-1.5 shadow-sm"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{savingGateway ? 'Saving...' : 'Save Gateway Credentials'}</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Email Alert Gateway (SMTP) Setup Box */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Inbox className="w-4 h-4 text-emerald-400 shrink-0" />
                <div>
                  <div className="text-xs font-semibold text-white flex items-center gap-2">
                    <span>Email Alert Gateway (SMTP)</span>
                    {emailGatewayInfo?.is_configured ? (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Active: {emailGatewayInfo.provider}
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        Unconfigured
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Deliver real warning messages directly to your inbox via Gmail, Outlook, or SMTP.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setEmailConfigOpen(!emailConfigOpen)}
                className="text-xs font-medium text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition-colors px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20"
              >
                <Settings2 className="w-3.5 h-3.5" />
                <span>{emailConfigOpen ? 'Hide' : 'Configure'}</span>
                {emailConfigOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            </div>

            {emailConfigOpen && (
              <div className="pt-3 border-t border-slate-800 space-y-3 animate-in fade-in">
                {emailGatewayNotice && (
                  <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-300 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
                    <span>{emailGatewayNotice}</span>
                  </div>
                )}
                {emailGatewayError && (
                  <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
                    <span>{emailGatewayError}</span>
                  </div>
                )}

                {/* Preset Provider Selector Tabs */}
                <div>
                  <label className="block text-[11px] font-semibold text-slate-300 mb-1.5">
                    Select Email Service Provider
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => handleSelectSmtpPreset('gmail')}
                      className={`px-2.5 py-2 rounded-xl text-xs font-semibold border flex items-center justify-center gap-1 transition-all ${
                        smtpPreset === 'gmail'
                          ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-300 shadow-sm'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <span>🚀 Gmail</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSelectSmtpPreset('outlook')}
                      className={`px-2.5 py-2 rounded-xl text-xs font-semibold border flex items-center justify-center gap-1 transition-all ${
                        smtpPreset === 'outlook'
                          ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-300 shadow-sm'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <span>✉️ Outlook</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSelectSmtpPreset('custom')}
                      className={`px-2.5 py-2 rounded-xl text-xs font-semibold border flex items-center justify-center gap-1 transition-all ${
                        smtpPreset === 'custom'
                          ? 'bg-emerald-500/20 border-emerald-500/60 text-emerald-300 shadow-sm'
                          : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <span>⚙️ Custom</span>
                    </button>
                  </div>
                </div>

                {/* SMTP Input Fields */}
                <div className="space-y-2.5 bg-slate-950/60 border border-slate-800/80 p-3 rounded-xl">
                  <div className="grid grid-cols-3 gap-2">
                    <div className="col-span-2">
                      <label className="block text-[10px] text-slate-400 mb-1">SMTP Host</label>
                      <input
                        type="text"
                        value={smtpHost}
                        onChange={(e) => setSmtpHost(e.target.value)}
                        placeholder="smtp.gmail.com"
                        className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-slate-400 mb-1">Port</label>
                      <input
                        type="number"
                        value={smtpPort}
                        onChange={(e) => setSmtpPort(e.target.value)}
                        placeholder="587"
                        className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[10px] text-slate-400 mb-1">Sender Email / Login Username</label>
                    <input
                      type="email"
                      value={smtpUser}
                      onChange={(e) => setSmtpUser(e.target.value)}
                      placeholder={emailGatewayInfo?.smtp_user_masked ? `Current: ${emailGatewayInfo.smtp_user_masked}` : 'your.email@gmail.com'}
                      className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-[10px] text-slate-400">
                        {smtpPreset === 'gmail' ? 'Google App Password' : 'SMTP Password'}
                      </label>
                      {smtpPreset === 'gmail' && (
                        <a
                          href="https://myaccount.google.com/apppasswords"
                          target="_blank"
                          rel="noreferrer"
                          className="text-[10px] text-emerald-400 hover:underline flex items-center gap-0.5"
                        >
                          Generate App Password <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      )}
                    </div>
                    <div className="relative">
                      <input
                        type={showSmtpPassword ? 'text' : 'password'}
                        value={smtpPassword}
                        onChange={(e) => setSmtpPassword(e.target.value)}
                        placeholder={emailGatewayInfo?.is_configured ? '••••••••••••••••' : (smtpPreset === 'gmail' ? '16-character App Password' : 'Password')}
                        className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 pr-10 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                      <button
                        type="button"
                        onClick={() => setShowSmtpPassword(!showSmtpPassword)}
                        className="text-slate-500 hover:text-slate-300 absolute right-3 top-2"
                      >
                        {showSmtpPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  {smtpPreset === 'gmail' && (
                    <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5 text-[11px] text-slate-300 space-y-1">
                      <div className="font-semibold text-emerald-400 text-[11px]">💡 Quick Gmail Setup:</div>
                      <div>1. Go to your <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" className="text-teal-300 underline font-medium">Google Account App Passwords</a>.</div>
                      <div>2. Create an App password (name it e.g. "Nidhi Pilot").</div>
                      <div>3. Paste the 16-character code above and click <strong>Save Email Gateway</strong>.</div>
                    </div>
                  )}

                  <div className="bg-slate-900/60 border border-slate-800/80 rounded-lg p-2.5 text-[11px] text-slate-400 flex items-start gap-2">
                    <Radio className="w-3.5 h-3.5 text-teal-400 mt-0.5 shrink-0" />
                    <span>
                      <strong className="text-slate-300">Network Note:</strong> Many home & mobile internet providers (Jio, Airtel, ACT) block raw outbound SMTP port 587. If a live connection drops, Nidhi Pilot automatically preserves your alerts in the <strong>In-App Alert Inbox</strong> below so no warning is ever lost.
                    </span>
                  </div>
                </div>

                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    onClick={handleSaveEmailGateway}
                    disabled={savingEmailGateway || !smtpHost.trim() || !smtpUser.trim() || (!smtpPassword.trim() && !emailGatewayInfo?.is_configured)}
                    className="px-3.5 py-2 text-xs font-semibold rounded-xl bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors disabled:opacity-40 flex items-center gap-1.5 shadow-sm"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{savingEmailGateway ? 'Saving...' : 'Save Email Gateway'}</span>
                  </button>
                </div>

                {emailLogs.length > 0 && (
                  <div className="pt-3 border-t border-slate-800 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                        <Inbox className="w-3.5 h-3.5 text-emerald-400" />
                        <span>In-App Email Alerts History</span>
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">{emailLogs.length} recent alerts</span>
                    </div>
                    <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                      {emailLogs.map((item) => (
                        <div
                          key={item.id}
                          className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-2.5 flex items-center justify-between gap-2 text-xs"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-1.5">
                              <span
                                className={`w-2 h-2 rounded-full shrink-0 ${
                                  item.status === 'delivered' ? 'bg-emerald-400' : 'bg-teal-400'
                                }`}
                              />
                              <p className="font-semibold text-slate-200 truncate text-[11px]">{item.subject}</p>
                            </div>
                            <p className="text-[10px] text-slate-400 truncate mt-0.5">
                              {new Date(item.dispatched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {item.provider}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => setPreviewEmail(item)}
                            className="px-2.5 py-1 text-[11px] font-semibold rounded-lg bg-teal-500/10 text-teal-300 border border-teal-500/30 hover:bg-teal-500/20 shrink-0 flex items-center gap-1 transition-all"
                          >
                            <Eye className="w-3 h-3" />
                            <span>Preview</span>
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>


          {/* Currency Preference */}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">
              Preferred Currency
            </label>
            <div className="relative">
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-10 pr-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors appearance-none cursor-pointer"
              >
                <option value="INR">INR (₹) - Indian Rupee</option>
                <option value="USD">USD ($) - US Dollar</option>
                <option value="EUR">EUR (€) - Euro</option>
                <option value="GBP">GBP (£) - British Pound</option>
              </select>
              <Coins className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
            </div>
          </div>

          {/* Change Password Section */}
          <div className="pt-2 border-t border-slate-800/80">
            <button
              type="button"
              onClick={() => setChangePasswordOpen(!changePasswordOpen)}
              className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1.5 transition-colors"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>{changePasswordOpen ? 'Cancel Password Change' : 'Change Password'}</span>
            </button>

            {changePasswordOpen && (
              <div className="mt-3.5 space-y-3 bg-slate-900/60 border border-slate-800 p-3.5 rounded-xl animate-in fade-in">
                <div>
                  <label className="block text-[11px] font-medium text-slate-300 mb-1">
                    Current Password
                  </label>
                  <div className="relative">
                    <input
                      type={showCurrentPassword ? 'text' : 'password'}
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      placeholder="Enter your current password"
                      className="w-full bg-slate-900 border border-slate-700/80 rounded-lg pl-3 pr-9 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      className="text-slate-400 hover:text-slate-200 absolute right-2.5 top-2 p-0.5"
                    >
                      {showCurrentPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-300 mb-1">
                    New Password
                  </label>
                  <div className="relative">
                    <input
                      type={showNewPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="At least 6 characters"
                      className="w-full bg-slate-900 border border-slate-700/80 rounded-lg pl-3 pr-9 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="text-slate-400 hover:text-slate-200 absolute right-2.5 top-2 p-0.5"
                    >
                      {showNewPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-300 mb-1">
                    Confirm New Password
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm your new password"
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="pt-3 border-t border-slate-800 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => {
                onClose();
                onLogout();
              }}
              className="flex items-center gap-1.5 px-3.5 py-2.5 text-xs font-semibold rounded-xl text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-rose-500/20 transition-all"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 text-xs font-semibold rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-xl bg-emerald-500 hover:bg-emerald-400 text-navy-950 transition-all shadow-md shadow-emerald-500/20 active:scale-95 disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{loading ? 'Saving...' : 'Save Changes'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>

      {previewEmail && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-navy-950/90 backdrop-blur-md animate-in fade-in">
          <div className="bg-navy-900 border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
              <div className="min-w-0 pr-3">
                <h4 className="text-sm font-bold text-white truncate">{previewEmail.subject}</h4>
                <p className="text-[11px] text-slate-400">
                  Target: {previewEmail.email} • {previewEmail.provider}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setPreviewEmail(null)}
                className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors shrink-0"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-3 bg-slate-950">
              <iframe
                title="Email Preview"
                srcDoc={previewEmail.html_body}
                className="w-full h-[420px] border-0 rounded-xl bg-transparent"
              />
            </div>
            <div className="p-3 border-t border-slate-800 flex justify-end bg-slate-900/80">
              <button
                type="button"
                onClick={() => setPreviewEmail(null)}
                className="px-4 py-1.5 text-xs font-semibold rounded-xl bg-slate-800 text-slate-200 hover:bg-slate-700 transition-colors"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
