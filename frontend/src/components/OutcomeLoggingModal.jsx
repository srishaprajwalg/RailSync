import { useState } from 'react';
import { recordOutcome } from '../services/api';
import { CheckCircle2, AlertTriangle, Clock, Train, X } from 'lucide-react';

export default function OutcomeLoggingModal({ task, isOpen, onClose, onOutcomeRecorded }) {
  const [actualDuration, setActualDuration] = useState(task ? task.duration_mins : 120);
  const [completionStatus, setCompletionStatus] = useState('COMPLETED');
  const [isSuccess, setIsSuccess] = useState(true);
  const [isRecurrence, setIsRecurrence] = useState(false);
  const [trainDelay, setTrainDelay] = useState(0);
  const [trainsImpacted, setTrainsImpacted] = useState(0);
  const [deviationReason, setDeviationReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen || !task) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      await recordOutcome({
        maintenance_request_id: task.id,
        actual_duration_minutes: Number(actualDuration),
        completion_status: completionStatus,
        success: isSuccess,
        recurrence: isRecurrence,
        train_delay_minutes: Number(trainDelay),
        trains_impacted: Number(trainsImpacted),
        deviation_reason: deviationReason || null,
      });
      setLoading(false);
      onOutcomeRecorded();
      onClose();
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95">
        
        {/* Header */}
        <div className="p-4 bg-rail-blue text-white flex justify-between items-center">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-green-400" />
            <h3 className="font-bold text-base">Record Actual Maintenance Outcome — {task.id}</h3>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white p-1 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded">{error}</div>
          )}

          <div>
            <span className="font-semibold text-gray-700">Activity: </span>
            <span className="font-bold text-gray-900">{task.task_type}</span> ({task.department})
            <p className="text-gray-500 mt-0.5">Location: Km {task.start_km.toFixed(1)} to {task.end_km.toFixed(1)} • Estimated: {task.duration_mins} mins</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-gray-700 mb-1">Actual Duration (Minutes):</label>
              <input
                type="number"
                min="10"
                value={actualDuration}
                onChange={(e) => setActualDuration(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded focus:bg-white text-sm"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Status:</label>
              <select
                value={completionStatus}
                onChange={(e) => setCompletionStatus(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded focus:bg-white text-sm"
              >
                <option value="COMPLETED">Completed Fully</option>
                <option value="PARTIAL">Partially Completed</option>
                <option value="ABORTED">Aborted Early</option>
                <option value="FAILED">Failed Quality Check</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-gray-700 mb-1">Train Delay Incurred (Mins):</label>
              <input
                type="number"
                min="0"
                value={trainDelay}
                onChange={(e) => setTrainDelay(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded focus:bg-white text-sm"
              />
            </div>

            <div>
              <label className="block font-semibold text-gray-700 mb-1">Trains Impacted (Count):</label>
              <input
                type="number"
                min="0"
                value={trainsImpacted}
                onChange={(e) => setTrainsImpacted(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded focus:bg-white text-sm"
              />
            </div>
          </div>

          <div className="flex items-center gap-6 py-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isSuccess}
                onChange={(e) => setIsSuccess(e.target.checked)}
                className="rounded text-rail-blue focus:ring-rail-blue"
              />
              <span className="font-semibold text-gray-700">Work Succeeded</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isRecurrence}
                onChange={(e) => setIsRecurrence(e.target.checked)}
                className="rounded text-red-600 focus:ring-red-600"
              />
              <span className="font-semibold text-red-700">Defect Recurrence</span>
            </label>
          </div>

          <div>
            <label className="block font-semibold text-gray-700 mb-1">Deviation Reason / Field Notes:</label>
            <textarea
              rows="2"
              value={deviationReason}
              onChange={(e) => setDeviationReason(e.target.value)}
              placeholder="E.g., Completed on time; ultrasonic weld testing passed."
              className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded focus:bg-white text-sm"
            />
          </div>

          <div className="pt-2 flex justify-end gap-2 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded font-medium"
            >
              {loading ? 'Saving Outcome...' : 'Confirm & Log Outcome'}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}
