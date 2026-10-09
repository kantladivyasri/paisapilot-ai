import React, { useState, useEffect } from 'react';
import {
  Search,
  Plus,
  FileSpreadsheet,
  Trash2,
  Edit2,
  Filter,
  CheckCircle2,
  Calendar,
  AlertCircle,
  Tag,
  CreditCard,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  Tags,
} from 'lucide-react';
import { api } from '../services/api';
import { formatINR, formatDate, getCategoryColor } from '../utils/formatters';
import ConfirmModal from '../components/ConfirmModal';
import CategoryModal from '../components/CategoryModal';

const PAYMENT_METHODS = [
  'all',
  'UPI',
  'Cash',
  'Credit Card',
  'Debit Card',
  'Net Banking',
];

export default function TransactionsPage({
  onOpenAddModal,
  onEditTransaction,
  onOpenImport,
  onClearAll,
}) {
  const [transactions, setTransactions] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 15;

  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedType, setSelectedType] = useState('all');
  const [selectedMethod, setSelectedMethod] = useState('all');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('desc');

  const [categoriesList, setCategoriesList] = useState([]);
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadCategories();
  }, []);

  useEffect(() => {
    fetchTransactions(currentPage);
  }, [
    currentPage,
    selectedCategory,
    selectedType,
    selectedMethod,
    startDate,
    endDate,
    sortBy,
    sortOrder,
  ]);

  const loadCategories = async () => {
    try {
      const cats = await api.getCategories();
      setCategoriesList(cats || []);
    } catch {
      // Fallback
    }
  };

  const fetchTransactions = async (page = 1) => {
    setLoading(true);
    try {
      const data = await api.getTransactions({
        category: selectedCategory !== 'All' ? selectedCategory : undefined,
        transaction_type: selectedType !== 'all' ? selectedType : undefined,
        payment_method: selectedMethod !== 'all' ? selectedMethod : undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        search: search.trim() || undefined,
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      });

      if (data && data.items !== undefined) {
        setTransactions(data.items);
        setTotalCount(data.total);
        setTotalPages(data.total_pages || 1);
        setCurrentPage(data.page || 1);
      } else if (Array.isArray(data)) {
        setTransactions(data);
        setTotalCount(data.length);
        setTotalPages(1);
        setCurrentPage(1);
      }
    } catch (err) {
      console.error('Failed to load transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchTransactions(1);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.deleteTransaction(deleteTarget.id);
      setDeleteTarget(null);
      fetchTransactions(currentPage);
    } catch (err) {
      alert(`Failed to delete transaction: ${err.message}`);
    } finally {
      setDeleting(false);
    }
  };

  const toggleSort = (col) => {
    if (sortBy === col) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(col);
      setSortOrder('desc');
    }
    setCurrentPage(1);
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Action Header & Filter Controls */}
      <div className="card-glass rounded-2xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          {/* Search bar */}
          <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search description, notes..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </form>

          {/* Action buttons */}
          <div className="flex items-center gap-3 w-full sm:w-auto justify-end flex-wrap">
            <button
              onClick={() => setIsCategoryModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl bg-slate-900 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-600 transition-all shadow-sm"
            >
              <Tags className="w-3.5 h-3.5 text-teal-400" />
              <span>Manage Categories</span>
            </button>

            {onClearAll && transactions.length > 0 && (
              <button
                onClick={onClearAll}
                title="Wipe demo records and start fresh"
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl text-slate-400 hover:text-rose-300 hover:bg-rose-500/10 border border-slate-800 hover:border-rose-500/30 transition-all"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                <span>Clear All</span>
              </button>
            )}

            <button
              onClick={onOpenImport}
              className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700/80 transition-all"
            >
              <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
              <span>Import CSV</span>
            </button>

            <button
              onClick={onOpenAddModal}
              className="flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl bg-emerald-500 text-navy-950 hover:bg-emerald-400 transition-all shadow-md shadow-emerald-500/20"
            >
              <Plus className="w-4 h-4" />
              <span>Add Expense / Income</span>
            </button>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-slate-800/80 text-xs">
          {/* Category Filter */}
          <div className="flex items-center gap-2">
            <Tag className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="All">All Categories</option>
              {categoriesList.map((c) => (
                <option key={c.id || c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          {/* Payment Method Filter */}
          <div className="flex items-center gap-2">
            <CreditCard className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedMethod}
              onChange={(e) => {
                setSelectedMethod(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="all">All Payment Methods</option>
              {PAYMENT_METHODS.filter((m) => m !== 'all').map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {/* Type Toggle */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
            {['all', 'expense', 'income'].map((t) => (
              <button
                key={t}
                onClick={() => {
                  setSelectedType(t);
                  setCurrentPage(1);
                }}
                className={`px-2.5 py-1 rounded text-[11px] font-semibold capitalize transition-all ${
                  selectedType === t
                    ? 'bg-slate-800 text-emerald-400 border border-slate-700 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Date Range Inputs */}
          <div className="flex items-center gap-2 text-slate-400">
            <Calendar className="w-3.5 h-3.5" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            />
            <span className="text-slate-600">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            />
            {(startDate || endDate || selectedCategory !== 'All' || selectedType !== 'all' || selectedMethod !== 'all' || search) && (
              <button
                onClick={() => {
                  setSelectedCategory('All');
                  setSelectedType('all');
                  setSelectedMethod('all');
                  setStartDate('');
                  setEndDate('');
                  setSearch('');
                  setCurrentPage(1);
                }}
                className="text-[11px] text-rose-400 hover:underline font-semibold ml-2"
              >
                Reset Filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Transaction Table */}
      <div className="card-glass rounded-2xl overflow-hidden border border-slate-800">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400">
            Fetching verified transactions...
          </div>
        ) : transactions.length === 0 ? (
          <div className="p-16 text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-slate-800/80 text-slate-400 flex items-center justify-center mx-auto border border-slate-700">
              <AlertCircle className="w-6 h-6" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-white">No Transactions Recorded Yet</h4>
              <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1">
                You currently have a clean slate. Record your actual expenses or income to start tracking your finances.
              </p>
            </div>
            <div>
              <button
                onClick={onOpenAddModal}
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl bg-emerald-500 text-navy-950 hover:bg-emerald-400 transition-all shadow-md shadow-emerald-500/20"
              >
                <Plus className="w-4 h-4 stroke-[2.5]" />
                <span>Add Your First Expense</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/60 border-b border-slate-800 text-slate-400 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th
                    className="py-3.5 px-6 cursor-pointer hover:text-white transition-colors"
                    onClick={() => toggleSort('date')}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Date</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th className="py-3.5 px-6">Description</th>
                  <th className="py-3.5 px-6">Category</th>
                  <th className="py-3.5 px-6">Payment Method</th>
                  <th className="py-3.5 px-6">Kind / Priority</th>
                  <th
                    className="py-3.5 px-6 text-right cursor-pointer hover:text-white transition-colors"
                    onClick={() => toggleSort('amount')}
                  >
                    <div className="flex items-center justify-end gap-1.5">
                      <span>Amount</span>
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </div>
                  </th>
                  <th className="py-3.5 px-6 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-medium">
                {transactions.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-6 text-slate-400 font-mono text-[11px] whitespace-nowrap">
                      {formatDate(t.date)}
                    </td>
                    <td className="py-3.5 px-6">
                      <div className="font-semibold text-slate-200">{t.description}</div>
                      {t.notes && (
                        <div className="text-[11px] text-slate-500 italic mt-0.5">{t.notes}</div>
                      )}
                    </td>
                    <td className="py-3.5 px-6 whitespace-nowrap">
                      <span
                        className="px-2.5 py-1 rounded-md text-[11px] font-semibold text-white/90 border border-slate-700"
                        style={{ backgroundColor: `${getCategoryColor(t.category)}20` }}
                      >
                        {t.category}
                      </span>
                    </td>
                    <td className="py-3.5 px-6 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-950 text-slate-300 border border-slate-800">
                        {t.payment_method || 'UPI'}
                      </span>
                    </td>
                    <td className="py-3.5 px-6 whitespace-nowrap">
                      {t.transaction_type === 'income' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          Income Inflow
                        </span>
                      ) : t.is_essential ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
                          Essential
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                          Discretionary
                        </span>
                      )}
                    </td>
                    <td
                      className={`py-3.5 px-6 text-right font-bold text-sm whitespace-nowrap ${
                        t.transaction_type === 'income' ? 'text-emerald-400' : 'text-slate-100'
                      }`}
                    >
                      {t.transaction_type === 'income' ? '+' : '-'}
                      {formatINR(t.amount)}
                    </td>
                    <td className="py-3.5 px-6 text-center whitespace-nowrap">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          onClick={() => onEditTransaction(t)}
                          title="Edit transaction"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => setDeleteTarget(t)}
                          title="Delete transaction"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-3.5 bg-slate-900/40 border-t border-slate-800 text-xs">
            <span className="text-slate-400">
              Showing page <strong className="text-white">{currentPage}</strong> of{' '}
              <strong className="text-white">{totalPages}</strong> ({totalCount} total records)
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Previous</span>
              </button>
              <button
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={Boolean(deleteTarget)}
        title="Delete Transaction?"
        message={`Are you sure you want to delete "${deleteTarget?.description}" (${formatINR(
          deleteTarget?.amount || 0
        )})? This will adjust your balances immediately.`}
        confirmText="Confirm Delete"
        confirmType="danger"
        loading={deleting}
        onConfirm={handleDeleteConfirm}
        onClose={() => setDeleteTarget(null)}
      />

      {/* Category Management Modal */}
      <CategoryModal
        isOpen={isCategoryModalOpen}
        onClose={() => setIsCategoryModalOpen(false)}
        onCategoriesUpdated={() => {
          loadCategories();
          fetchTransactions(currentPage);
        }}
      />
    </div>
  );
}
