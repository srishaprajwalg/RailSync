import { useState, useEffect } from 'react';
import { fetchPriorityDecision, fetchTaskPredictions, fetchTaskHistory } from '../services/api';
import { ShieldAlert, Brain, History, CheckCircle, X, Layers, Clock } from 'lucide-react';

export default function PriorityExplanationModal({ taskId, isOpen, onClose }) {
  const [loading, setLoading] = useState(true);
  const [decision, setDecision] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && taskId) {
      loadDetails();
    }
  }, [isOpen, taskId]);

  const loadDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const [pDec, pPreds, pHist] = await Promise.all([
        fetchPriorityDecision(taskId).catch(() => null),
        fetchTaskPredictions(taskId).catch(() => []),
        fetchTaskHistory(taskId).catch(() => []),
      ]);
      setDecision(pDec);
      setPredictions(pPreds);
      setHistory(pHist);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
        
        {/* Header */}
        <div className="p-4 bg-rail-blue text-white flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-rail-saffron" />
            <h3 className="font-bold text-lg">Explainable Priority & ML Intelligence — {taskId}</h3>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white p-1 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm">
          {loading ? (
            <div className="text-center py-10 text-gray-500">Loading explainability breakdown...</div>
          ) : error ? (
            <div className="bg-red-50 text-red-700 p-4 rounded">{error}</div>
          ) : (
            <>
              {/* Decision Score Banner */}
              {decision && (
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                  <div>
                    <span className="text-xs font-semibold text-blue-700 uppercase tracking-wider">Computed Priority</span>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-3xl font-bold text-blue-950">{decision.priority_score} / 100</span>
                      <span className={`text-xs font-bold uppercase px-2.5 py-1 rounded text-white ${
                        decision.priority_category === 'Critical' ? 'bg-red-600' : decision.priority_category === 'High' ? 'bg-orange-500' : decision.priority_category === 'Medium' ? 'bg-yellow-600' : 'bg-green-600'
                      }`}>
                        {decision.priority_category} Priority
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mt-2 italic">"{decision.reasoning}"</p>
                  </div>
                  <div className="text-xs text-gray-500 bg-white/80 p-2.5 rounded border border-blue-100 font-mono shrink-0">
                    Engine: {decision.engine_version}
                  </div>
                </div>
              )}

              {/* Mathematical Factor Breakdown */}
              {decision && (
                <div className="border border-gray-200 rounded-lg p-4 space-y-3">
                  <h4 className="font-bold text-gray-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-rail-blue" />
                    Exact Mathematical Factor Breakdown
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <div className="bg-gray-50 p-2.5 rounded border border-gray-100">
                      <span className="text-gray-500 text-[11px]">Severity Impact:</span>
                      <p className="text-base font-bold text-gray-800">+{decision.severity_score} pts</p>
                    </div>
                    <div className="bg-gray-50 p-2.5 rounded border border-gray-100">
                      <span className="text-gray-500 text-[11px]">Asset Criticality:</span>
                      <p className="text-base font-bold text-gray-800">+{decision.criticality_score} pts</p>
                    </div>
                    <div className="bg-gray-50 p-2.5 rounded border border-gray-100">
                      <span className="text-gray-500 text-[11px]">Deadline Urgency:</span>
                      <p className="text-base font-bold text-gray-800">+{decision.urgency_score} pts</p>
                    </div>
                    <div className="bg-gray-50 p-2.5 rounded border border-gray-100">
                      <span className="text-gray-500 text-[11px]">Overdue Penalty:</span>
                      <p className="text-base font-bold text-gray-800">+{decision.overdue_score} pts</p>
                    </div>
                    <div className="bg-gray-50 p-2.5 rounded border border-gray-100">
                      <span className="text-gray-500 text-[11px]">ML Recurrence Risk:</span>
                      <p className="text-base font-bold text-indigo-700">+{decision.ml_risk_score} pts</p>
                    </div>
                    <div className="bg-gray-50 p-2.5 rounded border border-gray-100">
                      <span className="text-gray-500 text-[11px]">Operational Corridor Weight:</span>
                      <p className="text-base font-bold text-gray-800">+{decision.operational_impact_score} pts</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Machine Learning Model Prediction */}
              {predictions.length > 0 && (
                <div className="border border-purple-200 bg-purple-50/50 rounded-lg p-4 space-y-2">
                  <div className="flex justify-between items-center">
                    <h4 className="font-bold text-purple-900 text-xs uppercase tracking-wider flex items-center gap-1.5">
                      <Brain className="w-4 h-4 text-purple-700" />
                      Trained ML Recurrence Risk Model
                    </h4>
                    <span className="text-[10px] font-mono text-purple-700 bg-purple-100 px-2 py-0.5 rounded">
                      {predictions[0].model_name} ({predictions[0].model_version})
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mt-2">
                    <div>
                      <span className="text-[11px] text-gray-500">Predicted Recurrence Probability:</span>
                      <p className="text-xl font-bold text-purple-950">{(predictions[0].probability * 100).toFixed(1)}%</p>
                    </div>
                    <div>
                      <span className="text-[11px] text-gray-500">Confidence:</span>
                      <p className="text-xl font-bold text-purple-950">{(predictions[0].confidence * 100).toFixed(0)}%</p>
                    </div>
                    <div>
                      <span className="text-[11px] text-gray-500">Classification:</span>
                      <p className="text-sm font-bold text-purple-800 mt-1">{predictions[0].prediction}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Asset Historical Failure Log */}
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-100 px-4 py-2 text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-1.5">
                  <History className="w-4 h-4 text-gray-600" />
                  Asset Maintenance & Failure History ({history.length} events)
                </div>
                <div className="divide-y divide-gray-100 max-h-40 overflow-y-auto text-xs">
                  {history.length === 0 ? (
                    <div className="p-4 text-center text-gray-500 italic">No previous failure history logged for this asset.</div>
                  ) : history.map(h => (
                    <div key={h.id} className="p-3 flex justify-between items-center hover:bg-gray-50">
                      <div>
                        <span className="font-semibold text-gray-800">{h.event_type} — {h.failure_type || 'General Service'}</span>
                        <p className="text-gray-500 text-[11px] mt-0.5">{h.notes || 'Logged repair event'} • Team: {h.team}</p>
                      </div>
                      <div className="text-right">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${h.recurrence ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-700'}`}>
                          {h.recurrence ? 'Recurrent' : 'Isolated'}
                        </span>
                        <div className="text-[10px] text-gray-500 mt-1">{h.duration_minutes} mins</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-gray-50 border-t border-gray-200 flex justify-end">
          <button onClick={onClose} className="px-4 py-1.5 bg-rail-blue text-white rounded font-medium text-xs hover:bg-rail-blue/90">
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
