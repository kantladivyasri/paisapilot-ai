import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Secure, beautifully styled Markdown renderer for PaisaPilot AI chatbot messages.
 * Uses react-markdown and remark-gfm with custom Tailwind typography mapping.
 * Protects against raw HTML execution while properly formatting:
 * - Headings (h1, h2, h3, h4)
 * - Bold / Italics (strong, em)
 * - Lists (ul, ol, li)
 * - Tables (table, thead, tbody, tr, th, td)
 * - Code blocks and inline code
 * - Paragraphs and blockquotes
 */
export default function MarkdownRenderer({ content }) {
  if (!content) return null;

  return (
    <div className="markdown-content text-xs leading-relaxed space-y-2 text-slate-100">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ node, ...props }) => (
            <h1 className="text-sm font-bold text-white mt-2 mb-1 border-b border-slate-800 pb-1" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-xs font-bold text-emerald-400 uppercase tracking-wide mt-2 mb-1" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-xs font-semibold text-teal-300 mt-1.5 mb-1" {...props} />
          ),
          h4: ({ node, ...props }) => (
            <h4 className="text-xs font-medium text-slate-200 mt-1 mb-0.5" {...props} />
          ),
          p: ({ node, ...props }) => (
            <p className="my-1 leading-relaxed text-slate-200 last:mb-0" {...props} />
          ),
          strong: ({ node, ...props }) => (
            <strong className="font-semibold text-white" {...props} />
          ),
          em: ({ node, ...props }) => (
            <em className="text-slate-300 italic" {...props} />
          ),
          ul: ({ node, ...props }) => (
            <ul className="list-disc list-outside pl-4 my-1.5 space-y-1 text-slate-200" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="list-decimal list-outside pl-4 my-1.5 space-y-1 text-slate-200" {...props} />
          ),
          li: ({ node, ...props }) => (
            <li className="leading-relaxed pl-0.5" {...props} />
          ),
          blockquote: ({ node, ...props }) => (
            <blockquote className="border-l-2 border-emerald-500 pl-3 my-2 italic text-slate-400 bg-slate-950/40 py-1 rounded-r" {...props} />
          ),
          table: ({ node, ...props }) => (
            <div className="overflow-x-auto my-2 rounded-xl border border-slate-800">
              <table className="min-w-full text-left text-xs divide-y divide-slate-800" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-slate-950 text-slate-300 font-semibold" {...props} />
          ),
          tbody: ({ node, ...props }) => (
            <tbody className="divide-y divide-slate-800/60 bg-slate-900/40" {...props} />
          ),
          tr: ({ node, ...props }) => (
            <tr className="hover:bg-slate-800/30 transition-colors" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th className="px-3 py-1.5 font-medium text-slate-300 uppercase text-[10px] tracking-wider" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="px-3 py-1.5 text-slate-300 font-mono text-[11px]" {...props} />
          ),
          code: ({ node, inline, ...props }) =>
            inline ? (
              <code className="bg-slate-950 px-1.5 py-0.5 rounded text-teal-300 font-mono text-[11px] border border-slate-800" {...props} />
            ) : (
              <div className="bg-slate-950 p-2.5 rounded-xl font-mono text-[11px] overflow-x-auto border border-slate-800 my-2 text-teal-300">
                <code {...props} />
              </div>
            ),
          hr: ({ node, ...props }) => (
            <hr className="my-2 border-slate-800" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
