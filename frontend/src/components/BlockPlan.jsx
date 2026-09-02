import { formatDuration, formatTime } from '../utils/formatters';
import { CheckCircle, MapPin, Clock, Info, Calendar } from 'lucide-react';

export default function BlockPlan({ blocks, tasks, timeWindow }) {
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
  // We use current date to anchor Day 0
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
                        <span className="text-[9px] font-bold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded uppercase">Consolidated</span>
                      )}
                    </div>
                    <ul className="space-y-2">
                      {blockTasks.map(t => (
                        <li key={t.id} className="flex justify-between items-start text-xs border-b border-gray-200/50 pb-2 last:border-0 last:pb-0">
                          <div className="flex flex-col gap-0.5">
                            <span className="text-gray-800 font-medium leading-tight">{t.task_type}</span>
                            <span className="text-[10px] font-bold text-gray-500">{t.department}</span>
                          </div>
                          <span className="text-[10px] font-medium text-gray-500 bg-white border border-gray-200 px-1.5 py-0.5 rounded shrink-0 ml-2">
                            {t.duration_mins} min
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Optimization Decision */}
                  <div className="flex items-start gap-2 bg-rail-bg p-3 rounded-md border border-rail-border/50">
                    <Info className="w-4 h-4 text-gray-500 shrink-0 mt-0.5" />
                    <p className="text-[11px] text-gray-600 leading-relaxed">
                      <strong>AI Coordination: </strong>
                      {isConsolidated 
                        ? "Tasks were grouped to minimize operational downtime, overlapping securely in time and space."
                        : "Task was scheduled into an optimized gap between passenger and freight train operations."}
                    </p>
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
