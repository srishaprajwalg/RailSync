import { formatDuration, formatTime } from '../utils/formatters';

export default function BlockPlan({ blocks, tasks }) {
  return (
    <div className="bg-white border border-rail-border rounded-lg shadow-sm h-full flex flex-col">
      <div className="p-4 border-b border-rail-border bg-rail-bg/50">
        <h3 className="text-lg font-semibold text-rail-text-dark">Optimized Blocks</h3>
        <p className="text-xs text-rail-text-muted">Consolidated multi-department plan</p>
      </div>
      <div className="p-4 flex-1 overflow-y-auto space-y-4">
        {blocks.map(block => {
          const duration = block.end_time_mins - block.start_time_mins;
          const blockTasks = block.assigned_tasks.map(tId => tasks.find(t => t.id === tId)).filter(Boolean);
          const depts = [...new Set(blockTasks.map(t => t.department))];
          
          return (
            <div key={block.id} className="border border-rail-border rounded p-3 hover:border-rail-saffron/50 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="text-xs font-mono bg-rail-bg text-rail-text-muted px-1.5 py-0.5 rounded">
                    BLK-{block.id.substring(0, 4)}
                  </span>
                  <div className="text-sm font-semibold mt-1">
                    {formatTime(block.start_time_mins)} - {formatTime(block.end_time_mins)} ({formatDuration(duration)})
                  </div>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  block.line_direction === 'Up' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'
                }`}>
                  {block.line_direction} Line
                </span>
              </div>
              
              <div className="text-xs text-rail-text-muted mb-3">
                Km {block.start_km.toFixed(1)} to Km {block.end_km.toFixed(1)}
              </div>
              
              <div className="space-y-2">
                <div className="flex flex-wrap gap-1 mb-2">
                  {depts.map(d => (
                    <span key={d} className="text-[10px] font-semibold bg-rail-saffron/10 text-rail-saffron px-1.5 py-0.5 rounded">
                      {d}
                    </span>
                  ))}
                  {blockTasks.length > 1 && (
                    <span className="text-[10px] font-semibold bg-rail-green/10 text-rail-green px-1.5 py-0.5 rounded">
                      Consolidated
                    </span>
                  )}
                </div>
                
                <div className="text-xs space-y-1 pl-2 border-l-2 border-rail-border">
                  {blockTasks.map(t => (
                    <div key={t.id} className="flex justify-between">
                      <span className="truncate pr-2">{t.task_type}</span>
                      <span className="text-rail-text-muted shrink-0">{t.duration_mins}m</span>
                    </div>
                  ))}
                </div>
                
                <p className="text-[10px] text-rail-text-muted italic pt-1">
                  {blockTasks.length > 1 
                    ? "Optimizer successfully found a safe window to consolidate these compatible tasks, minimizing overall downtime."
                    : "Optimizer found a safe window to execute this task without impacting train movements."}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
