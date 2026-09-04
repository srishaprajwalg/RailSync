import { useState } from 'react';
import { formatDuration, formatTime } from '../utils/formatters';
import { CheckCircle, MapPin, Clock, Info, Calendar, ChevronRight, X, Shield, FileText } from 'lucide-react';
import { fetchBlockDecisions } from '../services/api';

export default function BlockPlan({ blocks, tasks, timeWindow }) {
  const [selectedBlock, setSelectedBlock] = useState(null);
  const [blockDecisions, setBlockDecisions] = useState([]);
  const [loadingDecisions, setLoadingDecisions] = useState(false);

  const handleOpenDecisions = async (block) => {
    try {
      setSelectedBlock(block);
      setLoadingDecisions(true);
      const decs = await fetchBlockDecisions(block.id);
      setBlockDecisions(decs);
      setLoadingDecisions(false);
    } catch (err) {
      console.error('Failed to load block decisions:', err);
      setBlockDecisions([]);
      setLoadingDecisions(false);
    }
  };

  if (!blocks || blocks.length === 0) {
    return (
      <div className="bg-white border border-rail-border rounded-lg shadow-sm p-10 text-center">
        <Calendar className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-gray-800">No scheduled blocks</h3>
        <p className="text-gray-500 mt-1">There are no optimized maintenance windows for the selected time period.</p>
      </div>
    );
  }

  // Derive base date for calendar representation (similar to SimpleGanttView)
  const baseDate = new Date();
  baseDate.setHours(0, 0, 0, 0);

  const formatCalendarTime = (absoluteMins) => {
    const d = new Date(baseDate.getTime() + absoluteMins * 60000);
    const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const timeStr = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
    return `${dateStr} • ${timeStr}`;
  };

  return (
    <div className="bg-white border border-rail-border rounded-lg shadow-sm">
      {/* Decisions Trace Modal */}
      {selectedBlock && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
            <div className="p-4 bg-rail-blue text-white flex justify-between items-center">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-rail-saffron" />
                <h3 className="font-bold text-base">Schedule Decision Trace — Block {selectedBlock.id.substring(0, 8)}</h3>
              </div>
              <button onClick={() => setSelectedBlock(null)} className="text-white/80 hover:text-white p-1 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4 text-xs">
              <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                <p className="font-semibold text-gray-800 text-sm">{selectedBlock.reasoning}</p>
                <div className="flex gap-4 mt-2 text-gray-600">
                  <span><strong>Direction:</strong> {selectedBlock.line_direction} Line</span>
                  <span><strong>Span:</strong> Km {selectedBlock.start_km.toFixed(1)} to {selectedBlock.end_km.toFixed(1)}</span>
                  <span><strong>Duration:</strong> {formatDuration(selectedBlock.end_time_mins - selectedBlock.start_time_mins)}</span>
                </div>
              </div>

              <div>
                <h4 className="font-bold text-gray-700 uppercase tracking-wider text-[11px] mb-2">
                  Task Assignment Rationales ({selectedBlock.assigned_tasks.length})
                </h4>
                {loadingDecisions ? (
                  <div className="text-center py-6 text-gray-400">Loading verifiable solver decisions from PostgreSQL...</div>
                ) : blockDecisions.length === 0 ? (
                  <div className="text-gray-500 py-4 italic">No granular decision rows found for this block.</div>
                ) : (
                  <div className="space-y-3">
                    {blockDecisions.map(dec => {
                      const t = tasks.find(tsk => tsk.id === dec.maintenance_request_id);
                      return (
                        <div key={dec.id} className="p-3 bg-white border border-gray-200 rounded-lg shadow-2xs space-y-1.5">
                          <div className="flex justify-between items-center">
                            <span className="font-mono font-bold text-rail-blue">{dec.maintenance_request_id}</span>
                            <span className="text-[10px] font-semibold bg-blue-50 text-rail-blue px-2 py-0.5 rounded">
                              {dec.solver_reason || 'CP-SAT Interval'}
                            </span>
                          </div>
                          {t && <p className="text-xs font-medium text-gray-800">{t.task_type} ({t.department})</p>}
                          <p className="text-gray-600"><strong>Why Selected:</strong> {dec.why_selected}</p>
                          <p className="text-gray-600"><strong>Safety & Timetable:</strong> {dec.train_constraints}</p>
                          <p className="text-gray-600"><strong>Coordination:</strong> {dec.department_coordination}</p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <div className="p-3 bg-gray-50 border-t border-gray-200 flex justify-end">
              <button
                onClick={() => setSelectedBlock(null)}
                className="px-3 py-1.5 text-xs text-gray-600 hover:text-gray-800 rounded border border-gray-300 bg-white"
              >
                Close Trace
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="p-5 border-b border-gray-100 bg-gray-50/50">
        <h3 className="text-xl font-bold text-gray-800">Optimized Maintenance Action Plan</h3>
        <p className="text-sm text-gray-500 mt-1">Safe, coordinated maintenance windows prioritizing railway asset availability.</p>
      </div>
      
      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {blocks.map(block => {
            const duration = block.end_time_mins - block.start_time_mins;
            const blockTasks = block.assigned_tasks.map(tId => tasks.find(t => t.id === tId)).filter(Boolean);
            const isConsolidated = blockTasks.length > 1;
            const directionText = block.line_direction === 'Up' ? 'Toward Jolarpettai' : 'Toward Bengaluru';
            
            return (
              <div key={block.id} className="border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col h-full bg-white">
                
                {/* Header */}
                <div className="bg-rail-blue/5 px-4 py-3 border-b border-gray-100 flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold font-mono bg-white border border-rail-blue/20 text-rail-blue px-2 py-1 rounded shadow-sm">
                      BLK-{block.id.substring(0, 4)}
                    </span>
                    <span className="text-green-600 flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide bg-green-50 px-1.5 py-0.5 rounded">
                      <CheckCircle className="w-3 h-3" />
                      Safe
                    </span>
                  </div>
                  <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded ${
                    block.line_direction === 'Up' ? 'bg-indigo-50 text-indigo-700' : 'bg-fuchsia-50 text-fuchsia-700'
                  }`}>
                    {directionText}
                  </span>
                </div>
                
                {/* Content */}
                <div className="p-4 flex-1 flex flex-col space-y-4">
                  
                  {/* Where & When */}
                  <div className="grid grid-cols-1 gap-3">
                    <div className="flex items-start gap-2.5">
                      <Clock className="w-4 h-4 text-rail-blue mt-0.5 shrink-0" />
                      <div>
                        <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">Window</p>
                        <p className="text-xs font-medium text-gray-800 mt-0.5">{formatCalendarTime(block.start_time_mins)}</p>
                        <p className="text-xs font-medium text-gray-800">{formatCalendarTime(block.end_time_mins)}</p>
                        <p className="text-[11px] text-rail-blue font-medium mt-1 bg-blue-50 inline-block px-1.5 py-0.5 rounded">Duration: {formatDuration(duration)}</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-2.5">
                      <MapPin className="w-4 h-4 text-rail-blue mt-0.5 shrink-0" />
                      <div>
                        <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">Location</p>
                        <p className="text-sm font-medium text-gray-800 mt-0.5">Km {block.start_km.toFixed(1)} to Km {block.end_km.toFixed(1)}</p>
                        <p className="text-[11px] text-gray-500 mt-0.5">{(block.end_km - block.start_km).toFixed(1)} km span</p>
                      </div>
                    </div>
                  </div>

                  {/* Tasks */}
                  <div className="bg-gray-50 rounded-md p-3 border border-gray-100 flex-1">
                    <div className="flex justify-between items-center mb-2">
                      <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">Approved Work ({blockTasks.length})</p>
                      {isConsolidated && (
                        <span className="text-[9px] font-bold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded uppercase">Consolidated (Parallel)</span>
                      )}
                    </div>
                    {isConsolidated && (
                      <p className="text-[10px] text-gray-500 mb-2 italic bg-amber-50 p-1.5 rounded">
                        These {blockTasks.length} tasks run <strong>concurrently</strong> within the {formatDuration(duration)} block to save {(blockTasks.reduce((acc, t) => acc + t.duration_mins, 0) - duration)} minutes of downtime.
                      </p>
                    )}
                    <ul className="space-y-2 relative">
                      {blockTasks.map((t, idx) => (
                        <li key={t.id} className="flex justify-between items-start text-xs border-b border-gray-200/50 pb-2 last:border-0 last:pb-0 relative z-10">
                          <div className="flex flex-col gap-0.5">
                            <span className="text-gray-800 font-medium leading-tight">{t.task_type}</span>
                            <span className="text-[10px] font-bold text-gray-500">{t.department} • {t.required_resource || 'General Crew'}</span>
                          </div>
                          <span className="text-[10px] font-medium text-gray-500 bg-white border border-gray-200 px-1.5 py-0.5 rounded shrink-0 ml-2">
                            {t.duration_mins} min
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Optimization Decision */}
                  <div className="flex flex-col gap-2 bg-rail-bg p-3 rounded-md border border-rail-border/50">
                    <div className="flex items-start gap-2">
                      <Info className="w-4 h-4 text-rail-blue shrink-0 mt-0.5" />
                      <p className="text-[11px] text-gray-700 leading-relaxed">
                        <strong>AI Coordination: </strong>
                        {block.reasoning || (isConsolidated 
                          ? "Tasks were grouped to minimize operational downtime, overlapping securely in time and space."
                          : "Task was scheduled into an optimized gap between passenger and freight train operations.")}
                      </p>
                    </div>
                    <button
                      onClick={() => handleOpenDecisions(block)}
                      className="text-[10px] font-semibold text-rail-blue hover:text-blue-800 self-end flex items-center gap-0.5 transition-colors mt-0.5"
                    >
                      View Decision Trace <ChevronRight className="w-3 h-3" />
                    </button>
                  </div>
                  
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

