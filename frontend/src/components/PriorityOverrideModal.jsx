import React, { useState } from 'react';
import { overrideTaskPriority } from '../services/api';
import { ShieldAlert, CheckCircle, X, Sliders, UserCheck, AlertTriangle } from 'lucide-react';

export default function PriorityOverrideModal({ task, isOpen, onClose, onPriorityOverridden }) {
  const [overrideScore, setOverrideScore] = useState(task ? task.priority_details?.score || 50 : 50);
  const [overrideReason, setOverrideReason] = useState('');
  const [overriddenBy, setOverriddenBy] = useState('Senior Section Engineer (P-Way)');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen || !task) return null;

  const getCategory = (score) => {
    if (score >= 80) return { name: 'Critical', color: 'bg-red-100 text-red-800 border-red-300' };
    if (score >= 60) return { name: 'High', color: 'bg-orange-100 text-orange-800 border-orange-300' };
    if (score >= 40) return { name: 'Medium', color: 'bg-amber-100 text-amber-800 border-amber-300' };
    return { name: 'Low', color: 'bg-green-100 text-green-800 border-green-300' };
  };

  const previewCat = getCategory(overrideScore);
  const currentScore = task.priority_details?.score || 0;
  const currentCat = task.priority_details?.category || 'Low';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!overrideReason.trim() || overrideReason.trim().length < 5) {
      setError('Please provide a specific operational justification (minimum 5 characters).');
      return;
    }
    try {
      setSubmitting(true);
      setError(null);
      await overrideTaskPriority(task.id, {
        override_score: parseInt(overrideScore, 10),
        override_reason: overrideReason.trim(),
        overridden_by: overriddenBy.trim() || 'Divisional Controller',
      });
      setSubmitting(false);
      if (onPriorityOverridden) onPriorityOverridden();
      onClose();
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95">
        
        {/* Header */}
        <div className="p-4 bg-rail-blue text-white flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-rail-saffron" />
            <h3 className="font-bold text-base">Human Dispatcher Priority Override</h3>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white p-1 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          
          {/* Target Task Summary */}
          <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-xs font-mono font-bold text-rail-blue">{task.id}</span>
                <h4 className="text-sm font-semibold text-gray-800 mt-0.5">{task.task_type}</h4>
                <p className="text-xs text-gray-500">{task.department} • Km {task.start_km} to {task.end_km} ({task.line_direction} Line)</p>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-gray-500 uppercase font-semibold block">Current Score</span>
                <span className="text-sm font-bold text-gray-700">{currentScore} ({currentCat})</span>
              </div>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-xs p-2.5 rounded flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* New Priority Score Slider / Number */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs font-semibold text-gray-700">New Priority Score (0–100):</label>
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-rail-blue font-mono">{overrideScore}</span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${previewCat.color}`}>
                  {previewCat.name}
                </span>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={overrideScore}
              onChange={(e) => setOverrideScore(parseInt(e.target.value, 10))}
              className="w-full accent-rail-blue cursor-pointer h-2 bg-gray-200 rounded-lg"
            />
            <div className="flex justify-between text-[10px] text-gray-400 mt-1">
              <span>0 (Low)</span>
              <span>40 (Medium)</span>
              <span>60 (High)</span>
              <span>80 (Critical)</span>
              <span>100</span>
            </div>
          </div>

          {/* Justification Reason */}
          <div>
            <label className="text-xs font-semibold text-gray-700 block mb-1">
              Operational Justification <span className="text-red-500">*</span>
            </label>
            <textarea
              required
              rows="3"
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="e.g., Track Geometry Car identified gauge widening; mandated immediate speed restriction mitigation."
              className="w-full text-xs p-2.5 border border-gray-300 rounded-md focus:ring-1 focus:ring-rail-blue focus:border-rail-blue outline-none"
            />
          </div>

          {/* Overridden By */}
          <div>
            <label className="text-xs font-semibold text-gray-700 block mb-1">
              Authorized Dispatcher / Official
            </label>
            <div className="flex items-center gap-2 border border-gray-300 rounded-md px-2.5 py-1.5 bg-white">
              <UserCheck className="w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={overriddenBy}
                onChange={(e) => setOverriddenBy(e.target.value)}
                className="text-xs w-full outline-none"
                placeholder="Name or Role"
              />
            </div>
          </div>

          {/* Audit Note */}
          <div className="text-[11px] text-gray-500 bg-amber-50 p-2.5 rounded border border-amber-200/60">
            <span className="font-semibold text-amber-900">Traceability Notice:</span> This override will be recorded in the PostgreSQL audit log (`priority_decisions`) with timestamp and controller credentials.
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-800 rounded border border-gray-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-1.5 text-xs font-semibold text-white bg-rail-blue hover:bg-rail-blue/90 rounded shadow-sm disabled:opacity-50"
            >
              {submitting ? 'Applying Override...' : 'Apply Priority Override'}
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}
