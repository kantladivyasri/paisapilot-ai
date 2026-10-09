import React, { useState, useEffect } from 'react';
import { X, Key, CheckCircle, ShieldAlert, Sparkles, Eye, EyeOff } from 'lucide-react';
import { api } from '../services/api';

export default function SettingsModal({ isOpen, onClose, onSettingsUpdated }) {
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('llama-3.3-70b-versatile');
  const [configured, setConfigured] = useState(false);
  const [maskedKey, setMaskedKey] = useState('');
  const [showKey, setShowKey] = useState(false);

  const [geminiKey, setGeminiKey] = useState('');
  const [geminiModel, setGeminiModel] = useState('gemini-2.0-flash');
  const [geminiConfigured, setGeminiConfigured] = useState(false);
  const [maskedGeminiKey, setMaskedGeminiKey] = useState('');
  const [showGeminiKey, setShowGeminiKey] = useState(false);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);

  const loadSettings = async () => {
    setLoading(true);
    setMessage('');
    try {
      const data = await api.getSettings();
      setConfigured(data.groq_api_key_configured);
      setMaskedKey(data.groq_masked_key || '');
      setModel(data.groq_model || 'llama-3.3-70b-versatile');
      setGeminiConfigured(data.gemini_api_key_configured);
      setMaskedGeminiKey(data.gemini_masked_key || '');
      setGeminiModel(data.gemini_model || 'gemini-2.0-flash');
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage('');
    try {
      const payload = { groq_model: model, gemini_model: geminiModel };
      if (apiKey.trim()) {
        payload.groq_api_key = apiKey.trim();
      }
      if (geminiKey.trim()) {
        payload.gemini_api_key = geminiKey.trim();
      }
      const res = await api.updateSettings(payload);
      setConfigured(res.groq_api_key_configured);
      setGeminiConfigured(res.gemini_api_key_configured);
      setMessage('Settings updated successfully!');
      setApiKey('');
      setGeminiKey('');
      if (onSettingsUpdated) onSettingsUpdated();
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-navy-900 border border-slate-800 rounded-2xl w-full max-w-md overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
              <Key className="w-4 h-4" />
            </div>
            <h3 className="text-base font-bold text-white">AI Engine Configuration</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSave} className="p-6 space-y-4">
          {message && (
            <div className="p-3 text-xs rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
              {message}
            </div>
          )}

          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-1.5">
            <div className="flex items-center justify-between font-semibold text-slate-300">
              <span>Groq LLM Status:</span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] ${
                configured ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
              }`}>
                {configured ? 'Active' : 'Unset (Fallback Active)'}
              </span>
            </div>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              When an API key is provided, conversations leverage ultra-fast Groq LLM inference with strict deterministic grounding. If unset, the app operates 100% reliably with the built-in rule-based financial engine.
            </p>
          </div>

          {/* Groq API Key input */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Groq API Key {configured && <span className="text-emerald-400 text-[11px]">({maskedKey})</span>}
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                placeholder={configured ? 'Enter new key to update...' : 'gsk_...'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 pr-10"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-300"
              >
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Model selection */}
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Groq Model
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500"
            >
              <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (Recommended)</option>
              <option value="llama-3.1-8b-instant">llama-3.1-8b-instant (Fastest)</option>
              <option value="mixtral-8x7b-32768">mixtral-8x7b-32768</option>
            </select>
          </div>

          {/* Gemini API Key input (Optional alternative) */}
          <div className="pt-2 border-t border-slate-800/80">
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Google Gemini API Key (Optional) {geminiConfigured && <span className="text-blue-400 text-[11px]">({maskedGeminiKey})</span>}
            </label>
            <div className="relative">
              <input
                type={showGeminiKey ? 'text' : 'password'}
                placeholder={geminiConfigured ? 'Enter new key to update...' : 'AIzaSy...'}
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 pr-10"
              />
              <button
                type="button"
                onClick={() => setShowGeminiKey(!showGeminiKey)}
                className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-300"
              >
                {showGeminiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 text-xs font-bold text-navy-950 bg-teal-400 hover:bg-teal-300 rounded-xl transition-all shadow-md shadow-teal-500/20 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
