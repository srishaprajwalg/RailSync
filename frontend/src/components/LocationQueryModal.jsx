import { useState, useEffect } from 'react';
import { queryLocation } from '../services/api';
import { MapPin, Search, AlertCircle, Train, Wrench, Shield, X } from 'lucide-react';

export default function LocationQueryModal({ isOpen, onClose }) {
  const [chainage, setChainage] = useState(76.5);
  const [radius, setRadius] = useState(5.0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await queryLocation(chainage, radius);
      setResult(res);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      handleSearch();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
        
        {/* Header */}
        <div className="p-4 bg-rail-blue text-white flex justify-between items-center">
          <div className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-rail-saffron" />
            <h3 className="font-bold text-lg">Corridor Geospatial & Chainage Radius Query</h3>
          </div>
          <button onClick={onClose} className="text-white/80 hover:text-white p-1 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Controls */}
        <div className="p-4 bg-gray-50 border-b border-rail-border flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-gray-700">Target KM:</label>
            <input 
              type="number" 
              step="0.5" 
              value={chainage} 
              onChange={(e) => setChainage(parseFloat(e.target.value) || 0)}
              className="w-24 px-2.5 py-1 text-sm bg-white border border-gray-300 rounded font-mono"
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-gray-700">Radius (± KM):</label>
            <input 
              type="number" 
              step="0.5" 
              min="0.5" 
              max="50" 
              value={radius} 
              onChange={(e) => setRadius(parseFloat(e.target.value) || 1)}
              className="w-20 px-2.5 py-1 text-sm bg-white border border-gray-300 rounded font-mono"
            />
          </div>

          <button 
            onClick={handleSearch}
            disabled={loading}
            className="px-4 py-1.5 bg-rail-blue hover:bg-rail-blue/90 text-white rounded text-sm font-medium flex items-center gap-1.5 shadow-sm transition-colors"
          >
            <Search className="w-4 h-4" />
            {loading ? 'Querying DB...' : 'Execute Query'}
          </button>

          <span className="text-xs text-gray-500 ml-auto">
            Search Span: <strong className="text-gray-800">Km {(chainage - radius).toFixed(1)} — Km {(chainage + radius).toFixed(1)}</strong>
          </span>
        </div>

        {/* Results Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {error && (
            <div className="bg-red-50 text-red-700 p-3 rounded text-sm flex gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {result && (
            <>
              {/* Summary Metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <div className="text-xs text-blue-700 font-semibold uppercase flex items-center gap-1">
                    <Shield className="w-3.5 h-3.5" /> Railway Assets
                  </div>
                  <div className="text-2xl font-bold text-blue-900 mt-1">{result.assets_in_range.length}</div>
                  <div className="text-[11px] text-blue-600 mt-0.5">Physical track, points, signals, OHE</div>
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <div className="text-xs text-amber-700 font-semibold uppercase flex items-center gap-1">
                    <Wrench className="w-3.5 h-3.5" /> Maintenance Tasks
                  </div>
                  <div className="text-2xl font-bold text-amber-900 mt-1">{result.total_activities_count}</div>
                  <div className="text-[11px] text-amber-600 mt-0.5">Defects & planned activities</div>
                </div>

                <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                  <div className="text-xs text-purple-700 font-semibold uppercase flex items-center gap-1">
                    <Train className="w-3.5 h-3.5" /> Section Train Density
                  </div>
                  <div className="text-2xl font-bold text-purple-900 mt-1">{result.passing_trains_count}</div>
                  <div className="text-[11px] text-purple-600 mt-0.5">Passing train movements across horizon</div>
                </div>
              </div>

              {/* Assets List */}
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-100 px-4 py-2 text-xs font-bold text-gray-700 uppercase tracking-wider">
                  Assets Within KM Range ({result.assets_in_range.length})
                </div>
                <div className="divide-y divide-gray-100 max-h-48 overflow-y-auto text-xs">
                  {result.assets_in_range.length === 0 ? (
                    <div className="p-4 text-center text-gray-500 italic">No assets in this radius range.</div>
                  ) : result.assets_in_range.map(a => (
                    <div key={a.id} className="p-3 flex justify-between items-center hover:bg-gray-50">
                      <div>
                        <span className="font-bold text-gray-800">{a.asset_code}</span>
                        <span className="ml-2 text-[10px] bg-gray-200 px-1.5 py-0.5 rounded uppercase font-semibold text-gray-700">{a.asset_type}</span>
                        <span className="ml-1 text-[10px] bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded font-semibold">{a.department}</span>
                        <p className="text-gray-500 text-[11px] mt-0.5">Km {a.start_chainage.toFixed(1)} to Km {a.end_chainage.toFixed(1)} • Age: {a.age_years} yrs</p>
                      </div>
                      <div className="text-right">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                          a.criticality >= 4 ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                        }`}>
                          Crit L{a.criticality}
                        </span>
                        <div className="text-[10px] text-gray-500 mt-1">{a.status}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Maintenance Activities */}
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="bg-gray-100 px-4 py-2 text-xs font-bold text-gray-700 uppercase tracking-wider">
                  Maintenance Activities in Radius ({result.maintenance_activities.length})
                </div>
                <div className="divide-y divide-gray-100 max-h-56 overflow-y-auto text-xs">
                  {result.maintenance_activities.length === 0 ? (
                    <div className="p-4 text-center text-gray-500 italic">No maintenance activities reported in this range.</div>
                  ) : result.maintenance_activities.map(act => (
                    <div key={act.id} className="p-3 flex justify-between items-center hover:bg-gray-50">
                      <div>
                        <span className="font-bold text-gray-800">{act.task_type}</span>
                        <span className="ml-2 text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded font-semibold">{act.origin}</span>
                        <span className="ml-1 text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{act.department}</span>
                        <p className="text-gray-500 text-[11px] mt-0.5">Location: Km {act.start_km.toFixed(1)} – {act.end_km.toFixed(1)} • State: {act.status}</p>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] font-bold bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded">
                          Priority {act.priority_score} ({act.priority_category})
                        </span>
                        <div className="text-[10px] text-red-600 mt-1 font-semibold">Severity L{act.severity}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-gray-50 border-t border-gray-200 flex justify-between items-center text-xs text-gray-500">
          <span>Source: PostgreSQL Spatial / Chainage Range Engine</span>
          <button onClick={onClose} className="px-4 py-1.5 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded font-medium">
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
