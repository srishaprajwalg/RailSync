import { Clock, CheckCircle, Layers, Activity, AlertTriangle, AlertCircle, TrendingUp } from 'lucide-react';

export default function KPICards({ metrics }) {
  if (!metrics) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
      
      {/* Tasks Overview */}
      <div className="bg-white border border-rail-border rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-rail-text-muted">Task Processing</p>
          <Activity className="w-5 h-5 text-rail-blue opacity-80" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <p className="text-2xl font-semibold text-rail-text-dark">{metrics.planned_tasks}</p>
          <p className="text-xs text-rail-text-muted">/ {metrics.total_tasks} Planned</p>
        </div>
        <div className="mt-2 flex gap-3 text-xs">
          <span className="flex items-center gap-1 text-rail-saffron">
            <Clock className="w-3 h-3" /> {metrics.deferred_tasks} Deferred
          </span>
          <span className="flex items-center gap-1 text-rail-error">
            <AlertTriangle className="w-3 h-3" /> {metrics.infeasible_tasks} Infeasible
          </span>
        </div>
      </div>

      {/* High Priority Tasks */}
      <div className="bg-white border border-rail-border rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-rail-text-muted">High-Priority Tasks</p>
          <AlertCircle className="w-5 h-5 text-rail-saffron opacity-80" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <p className="text-2xl font-semibold text-rail-text-dark">{metrics.high_priority_planned}</p>
          <p className="text-xs text-rail-text-muted">Planned</p>
        </div>
        <div className="mt-2 text-xs text-rail-text-muted">
          <span className={metrics.high_priority_deferred > 0 ? "text-rail-error font-medium" : ""}>
            {metrics.high_priority_deferred} high-priority tasks deferred
          </span>
        </div>
      </div>

      {/* Blocks & Duration */}
      <div className="bg-white border border-rail-border rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-rail-text-muted">Consolidated Blocks</p>
          <Layers className="w-5 h-5 text-rail-blue opacity-80" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <p className="text-2xl font-semibold text-rail-text-dark">{metrics.blocks_created}</p>
          <p className="text-xs text-rail-text-muted">blocks scheduled</p>
        </div>
        <div className="mt-2 text-xs text-rail-text-muted">
          Total Block Time: <span className="font-medium text-rail-text-dark">{metrics.total_block_minutes} mins</span>
        </div>
      </div>

      {/* Downtime Reduction */}
      <div className="bg-rail-green/10 border border-rail-green/20 rounded-lg p-4 shadow-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 w-16 h-16 bg-rail-green/10 rounded-bl-full -mr-4 -mt-4"></div>
        <div className="flex items-center justify-between relative z-10">
          <p className="text-sm font-medium text-rail-green">Downtime Reduction</p>
          <TrendingUp className="w-5 h-5 text-rail-green" />
        </div>
        <div className="mt-2 flex items-baseline gap-2 relative z-10">
          <p className="text-2xl font-bold text-rail-green">{metrics.downtime_reduction_pct.toFixed(1)}%</p>
        </div>
        <div className="mt-2 text-xs text-rail-green opacity-80 relative z-10">
          {metrics.total_block_minutes} mins vs {metrics.total_requested_maintenance_minutes} requested
        </div>
      </div>
    </div>
  );
}
