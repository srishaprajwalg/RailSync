import { formatDuration, formatTime } from '../utils/formatters';
import { CheckCircle, MapPin, Clock, Info } from 'lucide-react';

export default function BlockPlan({ blocks, tasks }) {
  return (
    <div className="bg-white border border-rail-border rounded-lg shadow-sm h-full flex flex-col">
      <div className="p-5 border-b border-gray-100 bg-gray-50/50">
        <h3 className="text-xl font-bold text-gray-800">RailVyuha Action Plan</h3>
        <p className="text-sm text-gray-500 mt-1">AI-generated safe maintenance windows</p>
      </div>
      
      <div className="p-5 flex-1 overflow-y-auto space-y-6">
        {blocks.map(block => {
          const duration = block.end_time_mins - block.start_time_mins;
          const blockTasks = block.assigned_tasks.map(tId => tasks.find(t => t.id === tId)).filter(Boolean);
          const depts = [...new Set(blockTasks.map(t => t.department))];
          const isConsolidated = blockTasks.length > 1;
          const directionText = block.line_direction === 'Up' ? 'Toward Jolarpettai (Up Line)' : 'Toward Bengaluru (Down Line)';
          
          return (
            <div key={block.id} className="border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
              
              {/* Header */}
              <div className="bg-blue-50/50 px-4 py-3 border-b border-gray-100 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold font-mono bg-blue-100 text-blue-800 px-2 py-1 rounded">
                    BLK-{block.id.substring(0, 4)}
                  </span>
                  <span className="text-green-600 flex items-center gap-1 text-xs font-bold uppercase tracking-wide">
                    <CheckCircle className="w-3.5 h-3.5" />
                    Verified Safe
                  </span>
                </div>
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                  block.line_direction === 'Up' ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'bg-fuchsia-50 text-fuchsia-700 border border-fuchsia-100'
                }`}>
                  {directionText}
                </span>
              </div>
              
              {/* Content */}
              <div className="p-4 space-y-4">
                
                {/* Where & When */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-start gap-2">
                    <Clock className="w-4 h-4 text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">When</p>
                      <p className="text-sm font-medium text-gray-800">{formatTime(block.start_time_mins)} - {formatTime(block.end_time_mins)}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{formatDuration(duration)} reserved</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
                    <div>
                      <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">Where</p>
                      <p className="text-sm font-medium text-gray-800">Km {block.start_km.toFixed(1)} to Km {block.end_km.toFixed(1)}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{(block.end_km - block.start_km).toFixed(1)} km span</p>
                    </div>
                  </div>
                </div>

                {/* Tasks */}
                <div className="bg-gray-50 rounded-md p-3 border border-gray-100">
                  <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider mb-2">Approved Work</p>
                  <ul className="space-y-2">
                    {blockTasks.map(t => (
                      <li key={t.id} className="flex justify-between items-center text-sm">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-bold bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded">{t.department}</span>
                          <span className="text-gray-800">{t.task_type}</span>
                        </div>
                        <span className="text-xs font-medium text-gray-500 bg-white border border-gray-200 px-2 py-0.5 rounded shadow-sm">
                          {t.duration_mins} min
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* AI Explanation */}
                <div className="flex items-start gap-2 bg-blue-50/30 p-3 rounded-md">
                  <Info className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                  <p className="text-xs text-gray-600 leading-relaxed">
                    <strong>AI Decision: </strong>
                    {isConsolidated 
                      ? "These compatible tasks were grouped together into a single track possession because they overlap in time and location. This reduces overall downtime and prevents multiple separate disruptions."
                      : "This task was successfully scheduled into a safe window without conflicting with any passenger or freight train movements."}
                  </p>
                </div>
                
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
