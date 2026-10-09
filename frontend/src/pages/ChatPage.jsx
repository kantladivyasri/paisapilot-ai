import React, { useState, useRef, useEffect } from 'react';
import {
  Bot,
  Send,
  User,
  Sparkles,
  Zap,
  HelpCircle,
  TrendingUp,
  Wallet,
  RotateCcw,
  Trash2,
} from 'lucide-react';
import { api } from '../services/api';
import { formatINR } from '../utils/formatters';
import MarkdownRenderer from '../components/MarkdownRenderer';

const ENHANCED_PROMPTS = [
  'Predict my monthly expenses and savings',
  'Am I spending too much on unwanted things than regular?',
  'How much money did I spend this week?',
  'What is my biggest expense category this month?',
  'How much money do I have left from my salary?',
  'How much did I spend on food in September?',
  'Compare my spending this month with last month.',
  'How can I save ₹5,000 every month?',
  'Am I spending too much on shopping?',
  'Show my total expenses for this year.',
  'Which expenses can I reduce?',
  'Can I afford an additional ₹2,000 expense?',
];

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    loadChatHistory();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const loadChatHistory = async () => {
    setInitialLoading(true);
    try {
      const history = await api.getChatHistory();
      if (history && history.length > 0) {
        const formatted = history.map((m) => ({
          id: m.id,
          sender: m.role === 'user' ? 'user' : 'assistant',
          text: m.content,
          engine: m.engine || 'groq',
          engineName: m.engine === 'groq' ? 'Groq LLM' : m.engine || 'AI Assistant',
          timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }));
        setMessages(formatted);
      } else {
        setMessages([
          {
            id: 1,
            sender: 'assistant',
            text: "Namaste! I'm **PaisaPilot AI**, your personal finance assistant powered by Groq LLM and direct SQLite database tools.\n\nAsk me about your weekly spending, salary balances, category comparisons, or affordability simulations!",
            engine: 'groq',
            engineName: 'Groq LLM',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ]);
      }
    } catch {
      setMessages([
        {
          id: 1,
          sender: 'assistant',
          text: "Namaste! I'm **PaisaPilot AI**, your personal finance assistant. Ask me questions about your income, spending, or savings plans!",
          engine: 'groq',
          engineName: 'Groq LLM',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setInitialLoading(false);
    }
  };

  const handleSendMessage = async (queryText) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await api.sendChatMessage(textToSend.trim());
      const botMsg = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: res.reply,
        engine: res.engine,
        engineName: res.engine_name,
        structuredData: res.structured_data,
        suggestedPrompts: res.suggested_prompts,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      const errorMsg = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: `⚠️ Error fetching response: ${err.message}. Please check backend connection.`,
        engine: 'deterministic',
        engineName: 'System Fallback',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm('Clear all conversation history?')) return;
    try {
      await api.clearChatHistory();
      setMessages([
        {
          id: Date.now(),
          sender: 'assistant',
          text: 'Conversation history cleared. What financial questions would you like to explore?',
          engine: 'groq',
          engineName: 'Groq LLM',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } catch (err) {
      alert(`Failed to clear history: ${err.message}`);
    }
  };

  return (
    <div className="p-8 max-w-5xl mx-auto flex flex-col h-[calc(100vh-5rem)]">
      {/* Chat Container */}
      <div className="card-glass rounded-3xl flex flex-col flex-1 overflow-hidden border border-slate-800 shadow-2xl">
        {/* Chat Header */}
        <div className="px-6 py-4 bg-navy-900/80 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-navy-950 shadow-md shadow-emerald-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                PaisaPilot AI Financial Assistant
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Tool-Grounded & Context-Aware
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Connected to live database queries • Groq LLM inference
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={handleClearHistory}
              title="Clear conversation history"
              className="p-2 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={loadChatHistory}
              title="Refresh conversation"
              className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {initialLoading ? (
            <div className="flex items-center justify-center h-full text-xs text-slate-400">
              Loading conversation history...
            </div>
          ) : (
            messages.map((m) => {
              const isUser = m.sender === 'user';
              return (
                <div
                  key={m.id}
                  className={`flex gap-3.5 ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  {!isUser && (
                    <div className="w-8 h-8 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div className={`space-y-1.5 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
                    {/* Engine attribution badge */}
                    {!isUser && (
                      <div className="flex items-center gap-2 text-[10px] text-slate-400 font-medium">
                        <span className="px-2 py-0.5 rounded-full bg-slate-900 border border-slate-800 flex items-center gap-1">
                          {m.engine === 'groq' ? (
                            <Sparkles className="w-3 h-3 text-teal-400" />
                          ) : m.engine === 'gemini' ? (
                            <Sparkles className="w-3 h-3 text-blue-400" />
                          ) : (
                            <Zap className="w-3 h-3 text-emerald-400" />
                          )}
                          {m.engineName || 'PaisaPilot Engine'}
                        </span>
                        <span>{m.timestamp}</span>
                      </div>
                    )}

                    {/* Bubble */}
                    <div
                      className={`rounded-2xl px-5 py-3.5 text-xs leading-relaxed ${
                        isUser
                          ? 'bg-emerald-500 text-navy-950 font-semibold rounded-tr-none shadow-md shadow-emerald-500/10 whitespace-pre-wrap'
                          : 'bg-slate-900/90 border border-slate-800 text-slate-100 rounded-tl-none'
                      }`}
                    >
                      {isUser ? (
                        m.text
                      ) : (
                        <MarkdownRenderer content={m.text} />
                      )}
                    </div>

                    {/* Optional suggested followups */}
                    {!isUser && m.suggestedPrompts && m.suggestedPrompts.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {m.suggestedPrompts.map((p, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleSendMessage(p)}
                            className="text-[10px] font-medium px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 hover:text-emerald-400 hover:border-emerald-500/30 transition-all"
                          >
                            {p}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {isUser && (
                    <div className="w-8 h-8 rounded-xl bg-slate-800 text-slate-300 flex items-center justify-center shrink-0 mt-0.5">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              );
            })
          )}

          {loading && (
            <div className="flex gap-3.5 items-start">
              <div className="w-8 h-8 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 animate-pulse" />
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-900/80 border border-slate-800 rounded-tl-none flex items-center gap-2 text-xs text-slate-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce"></span>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.2s]"></span>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-bounce [animation-delay:0.4s]"></span>
                <span className="ml-1 text-[11px]">Executing database tools & generating response...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Chips */}
        <div className="px-6 py-2.5 bg-navy-950/40 border-t border-slate-800/80 overflow-x-auto flex items-center gap-2 shrink-0">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider shrink-0 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-emerald-400" /> Prompts:
          </span>
          {ENHANCED_PROMPTS.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(prompt)}
              className="text-[11px] whitespace-nowrap px-3 py-1 rounded-full bg-slate-900 hover:bg-emerald-500/10 text-slate-300 hover:text-emerald-300 border border-slate-800 hover:border-emerald-500/30 transition-all font-medium"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-navy-900 border-t border-slate-800 shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              placeholder="Ask anything (e.g. How much did I spend this week? / What is my biggest category?)..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-800 rounded-2xl px-4 py-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="px-5 py-3 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-navy-950 font-bold text-xs transition-all shadow-md shadow-emerald-500/20 disabled:opacity-50 flex items-center gap-1.5"
            >
              <Send className="w-4 h-4" />
              <span>Send</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
