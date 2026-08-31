import { Clock, Layers, Activity, AlertTriangle, AlertCircle, TrendingUp } from 'lucide-react';

export default function KPICards({ metrics }) {
  if (!metrics) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
      
      {/* Tasks Overview */}
      <div className="bg-white border border-rail-border rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between mb-1">
          <p className="text-sm font-semibold text-rail-text-dark">Maintenance Requests Processed</p>
          <Activity className="w-5 h-5 text-rail-blue opacity-80" />
        </div>
        <p className="text-[10px] text-gray-500 mb-3">RailVyuha AI scheduling decisions</p>
        
        <div className="flex items-baseline gap-2 mb-3">
          <p className="text-3xl font-bold text-gray-800">{metrics.planned_tasks}</p>
          <p className="text-xs text-gray-500">/ {metrics.total_tasks} Successfully Scheduled</p>
        </div>
        <div className="flex gap-4 text-xs font-medium">
          <span className="flex items-center gap-1 text-amber-600" title="Feasible but postponed to prioritize more critical work.">
            <Clock className="w-3 h-3" /> {metrics.deferred_tasks} Postponed
          </span>
          <span className="flex items-center gap-1 text-red-600" title="Cannot be safely scheduled before deadline due to train traffic.">
            <AlertTriangle className="w-3 h-3" /> {metrics.infeasible_tasks} Cannot Schedule
          </span>
        </div>
      </div>

      {/* High Priority Tasks */}
      <div className="bg-white border border-rail-border rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between mb-1">
          <p className="text-sm font-semibold text-rail-text-dark">Critical Safety Tasks</p>
          <AlertCircle className="w-5 h-5 text-amber-500 opacity-80" />
        </div>
        <p className="text-[10px] text-gray-500 mb-3">High-priority and urgent defect repairs</p>

        <div className="flex items-baseline gap-2 mb-3">
          <p className="text-3xl font-bold text-gray-800">{metrics.high_priority_planned}</p>
          <p className="text-xs text-gray-500">Scheduled safely</p>
        </div>
        <div className="text-xs">
          <span className={metrics.high_priority_deferred > 0 ? "text-red-600 font-semibold" : "text-gray-500"}>
            {metrics.high_priority_deferred > 0 
              ? `⚠️ ${metrics.high_priority_deferred} urgent tasks could not be scheduled` 
              : "✓ All urgent tasks scheduled"}
          </span>
        </div>
      </div>

      {/* Blocks & Duration */}
      <div className="bg-white border border-rail-border rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between mb-1">
          <p className="text-sm font-semibold text-rail-text-dark">Maintenance Blocks</p>
          <Layers className="w-5 h-5 text-rail-blue opacity-80" />
        </div>
        <p className="text-[10px] text-gray-500 mb-3">Grouped work windows created by RailVyuha</p>

        <div className="flex items-baseline gap-2 mb-3">
          <p className="text-3xl font-bold text-gray-800">{metrics.blocks_created}</p>
          <p className="text-xs text-gray-500">windows reserved on track</p>
        </div>
        <div className="text-xs text-gray-600 font-medium">
          Total Track Reserved Time: <span className="text-gray-900">{metrics.total_block_minutes} minutes</span>
        </div>
      </div>

      {/* Downtime Reduction */}
      <div className="bg-green-50 border border-green-100 rounded-lg p-4 shadow-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 w-20 h-20 bg-green-100 rounded-bl-full -mr-6 -mt-6"></div>
        <div className="flex items-center justify-between relative z-10 mb-1">
          <p className="text-sm font-semibold text-green-800">Track Uptime Saved</p>
          <TrendingUp className="w-5 h-5 text-green-700" />
        </div>
        <p className="text-[10px] text-green-700/80 mb-3 relative z-10">Efficiency gained through smart grouping</p>

        <div className="flex items-baseline gap-2 relative z-10 mb-3">
          <p className="text-3xl font-bold text-green-700">{metrics.downtime_reduction_pct.toFixed(1)}%</p>
        </div>
        <div className="text-xs text-green-800 font-medium relative z-10">
          Only {metrics.total_block_minutes} mins used to complete {metrics.total_requested_maintenance_minutes} mins of work
        </div>
      </div>
      
    </div>
  );
}
