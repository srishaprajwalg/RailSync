import { Clock, CheckCircle, Layers, Activity } from 'lucide-react';

export default function KPICards({ metrics }) {
  if (!metrics) return null;
  
  const reductionPercent = Math.round(((metrics.total_requested_mins - metrics.optimized_block_mins) / metrics.total_requested_mins) * 100);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div className="bg-white border border-rail-border rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-rail-text-muted">Total Tasks (Requested)</p>
          <Activity className="w-5 h-5 text-rail-blue opacity-80" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <p className="text-2xl font-semibold text-rail-text-dark">{metrics.total_tasks}</p>
          <p className="text-xs text-rail-text-muted">({metrics.total_requested_mins} mins total)</p>
        </div>
      </div>

      <div className="bg-white border border-rail-border rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-rail-text-muted">Tasks Planned safely</p>
          <CheckCircle className="w-5 h-5 text-rail-green opacity-80" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <p className="text-2xl font-semibold text-rail-text-dark">{metrics.granted_tasks}</p>
          <p className="text-xs text-rail-text-muted">({Math.round((metrics.granted_tasks/metrics.total_tasks)*100)}% completion)</p>
        </div>
      </div>

      <div className="bg-white border border-rail-border rounded-lg p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-rail-text-muted">Consolidated Blocks</p>
          <Layers className="w-5 h-5 text-rail-saffron opacity-80" />
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <p className="text-2xl font-semibold text-rail-text-dark">{metrics.blocks_created}</p>
          <p className="text-xs text-rail-text-muted">from {metrics.granted_tasks} requests</p>
        </div>
      </div>

      <div className="bg-rail-green/10 border border-rail-green/20 rounded-lg p-4 shadow-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 w-16 h-16 bg-rail-green/10 rounded-bl-full -mr-4 -mt-4"></div>
        <div className="flex items-center justify-between relative z-10">
          <p className="text-sm font-medium text-rail-green">Downtime Reduction</p>
          <Clock className="w-5 h-5 text-rail-green" />
        </div>
        <div className="mt-2 flex items-baseline gap-2 relative z-10">
          <p className="text-2xl font-bold text-rail-green">{reductionPercent}%</p>
          <p className="text-xs text-rail-green opacity-80">({metrics.optimized_block_mins} mins vs {metrics.total_requested_mins})</p>
        </div>
      </div>
    </div>
  );
}
