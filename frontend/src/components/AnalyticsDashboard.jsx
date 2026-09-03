import React, { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Activity, CheckCircle2, Clock, AlertTriangle, Layers, Zap, MapPin } from 'lucide-react';

export default function AnalyticsDashboard({ tasks, blocks, taskStatuses, metrics, corridor }) {
  
  // -- Data Processing for Analytics --
  
  // 1. Lifecycle distribution
  const lifecycleCounts = useMemo(() => {
    const counts = { Reported: 0, Prioritized: 0, 'In Progress': 0, Completed: 0 };
    tasks.forEach(t => {
      if (counts[t.lifecycle_status] !== undefined) {
        counts[t.lifecycle_status]++;
      }
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value })).filter(d => d.value > 0);
  }, [tasks]);

  const LIFECYCLE_COLORS = { Reported: '#9ca3af', Prioritized: '#3b82f6', 'In Progress': '#f59e0b', Completed: '#10b981' };

  // 2. Department Workload
  const departmentStats = useMemo(() => {
    const depts = {};
    tasks.forEach(t => {
      if (!depts[t.department]) depts[t.department] = { name: t.department, Active: 0, Completed: 0 };
      if (t.lifecycle_status === 'Completed') depts[t.department].Completed++;
      else depts[t.department].Active++;
    });
    return Object.values(depts).sort((a, b) => (b.Active + b.Completed) - (a.Active + a.Completed));
  }, [tasks]);

  // 3. Planning Outcome
  const planningCounts = useMemo(() => {
    const counts = { Planned: 0, Deferred: 0, Infeasible: 0, Pending: 0 };
    tasks.forEach(t => {
      if (t.lifecycle_status === 'Completed') return; // Skip completed for active planning
      const status = taskStatuses[t.id] || 'Pending';
      if (counts[status] !== undefined) counts[status]++;
    });
    return Object.entries(counts).map(([name, value]) => ({ name, value })).filter(d => d.value > 0);
  }, [tasks, taskStatuses]);

  const PLANNING_COLORS = { Planned: '#10b981', Deferred: '#f59e0b', Infeasible: '#ef4444', Pending: '#d1d5db' };

  // 4. Hotspots (binned by 20km intervals)
  const hotspots = useMemo(() => {
    const bins = Array.from({ length: 8 }, (_, i) => ({
      range: `${i * 20}-${(i + 1) * 20}km`,
      tasks: 0,
      minKm: i * 20,
      maxKm: (i + 1) * 20
    }));
    tasks.forEach(t => {
      const midPoint = (t.start_km + t.end_km) / 2;
      const binIndex = Math.min(Math.floor(midPoint / 20), 7);
      if (bins[binIndex]) bins[binIndex].tasks++;
    });
    return bins.filter(b => b.tasks > 0);
  }, [tasks]);

  // 5. Resource Demand
  const resourceStats = useMemo(() => {
    const counts = {};
    tasks.forEach(t => {
      if (t.lifecycle_status === 'Completed') return;
      const res = t.required_resource || 'General Crew';
      if (!counts[res]) counts[res] = 0;
      counts[res]++;
    });
    return Object.entries(counts).map(([name, Demand]) => ({ name, Demand })).sort((a, b) => b.Demand - a.Demand);
  }, [tasks]);

  // 6. Key Insights Generator
  const insights = useMemo(() => {
    const generated = [];
    
    // Dept insight
    if (departmentStats.length > 0) {
      const highestDept = departmentStats[0];
      generated.push(`**${highestDept.name}** currently has the highest workload with ${highestDept.Active} active requests.`);
    }
    
    // Infeasible insight
    const infeasible = planningCounts.find(p => p.name === 'Infeasible')?.value || 0;
    if (infeasible > 0) {
      generated.push(`**${infeasible} tasks** were rejected by CP-SAT because no mathematically safe maintenance window exists before their deadline.`);
    }

    // Consolidation insight
    if (metrics && metrics.blocks_created > 0 && metrics.planned_tasks > 0) {
      if (metrics.planned_tasks > metrics.blocks_created) {
        generated.push(`RailVyuha successfully consolidated **${metrics.planned_tasks} tasks** into just **${metrics.blocks_created} coordinated blocks**, saving track capacity.`);
      } else {
        generated.push(`Scheduled **${metrics.planned_tasks} tasks** into ${metrics.blocks_created} blocks.`);
      }
    }
    
    // Downtime insight
    if (metrics && metrics.downtime_reduction_pct > 0) {
      generated.push(`Block consolidation reduced total required track downtime by **${metrics.downtime_reduction_pct.toFixed(1)}%** compared to standalone scheduling.`);
    }

    return generated;
  }, [departmentStats, planningCounts, metrics]);


  // Helper component for KPI Cards
  const KPICard = ({ title, value, sub, icon: Icon, colorClass }) => (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-rail-border flex items-center gap-4">
      <div className={`p-3 rounded-full ${colorClass}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <div className="text-2xl font-bold text-gray-800">{value}</div>
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{title}</div>
        {sub && <div className="text-[10px] text-gray-400 mt-1">{sub}</div>}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      
      {/* Top Level KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard 
          title="Total Requests" 
          value={tasks.length} 
          sub={`${tasks.filter(t => t.lifecycle_status !== 'Completed').length} Active / ${tasks.filter(t => t.lifecycle_status === 'Completed').length} History`}
          icon={Layers} 
          colorClass="bg-blue-100 text-blue-600" 
        />
        <KPICard 
          title="Tasks Planned" 
          value={metrics ? metrics.planned_tasks : 0} 
          sub={metrics ? `Out of ${metrics.total_tasks} active` : 'Run optimizer to see'}
          icon={CheckCircle2} 
          colorClass="bg-green-100 text-green-600" 
        />
        <KPICard 
          title="Blocks Created" 
          value={metrics ? metrics.blocks_created : 0} 
          sub={metrics ? `${Math.round(metrics.total_block_minutes / 60)} hrs of downtime` : 'Run optimizer to see'}
          icon={Activity} 
          colorClass="bg-purple-100 text-purple-600" 
        />
        <KPICard 
          title="Downtime Saved" 
          value={metrics ? `${metrics.downtime_reduction_pct.toFixed(0)}%` : '0%'} 
          sub="Via block consolidation"
          icon={Zap} 
          colorClass="bg-amber-100 text-amber-600" 
        />
      </div>

      {/* Key Insights */}
      <div className="bg-rail-blue/5 border border-rail-blue/20 p-5 rounded-lg shadow-sm">
        <h3 className="text-sm font-bold text-rail-blue flex items-center gap-2 mb-3">
          <Zap className="w-4 h-4 fill-current" /> Decision Intelligence Insights
        </h3>
        <ul className="space-y-2">
          {insights.length > 0 ? insights.map((insight, idx) => (
            <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
              <span className="text-rail-saffron mt-0.5">•</span>
              <span dangerouslySetInnerHTML={{ __html: insight.replace(/\*\*(.*?)\*\*/g, '<span class="font-bold text-gray-900">$1</span>') }} />
            </li>
          )) : (
            <li className="text-sm text-gray-500 italic">Run the CP-SAT optimizer to generate insights.</li>
          )}
        </ul>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Department Workload */}
        <div className="bg-white p-5 rounded-lg shadow-sm border border-rail-border">
          <h3 className="text-sm font-bold text-gray-800 mb-1">Department Workload</h3>
          <p className="text-xs text-gray-500 mb-4">Active vs Completed tasks by department</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={departmentStats} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{fontSize: 10}} />
                <YAxis tick={{fontSize: 10}} />
                <RechartsTooltip cursor={{fill: '#f3f4f6'}} contentStyle={{fontSize: '12px'}} />
                <Legend wrapperStyle={{fontSize: '11px'}} />
                <Bar dataKey="Active" stackId="a" fill="#3b82f6" />
                <Bar dataKey="Completed" stackId="a" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Corridor Hotspots */}
        <div className="bg-white p-5 rounded-lg shadow-sm border border-rail-border">
          <h3 className="text-sm font-bold text-gray-800 mb-1 flex items-center gap-1"><MapPin className="w-4 h-4"/> Maintenance Hotspots</h3>
          <p className="text-xs text-gray-500 mb-4">Task distribution along the active corridor</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hotspots} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="range" tick={{fontSize: 10}} />
                <YAxis tick={{fontSize: 10}} />
                <RechartsTooltip cursor={{fill: '#f3f4f6'}} contentStyle={{fontSize: '12px'}} />
                <Bar dataKey="tasks" fill="#8b5cf6" name="Total Tasks" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Task Lifecycle Distribution */}
        <div className="bg-white p-5 rounded-lg shadow-sm border border-rail-border">
          <h3 className="text-sm font-bold text-gray-800 mb-1">Operational Lifecycle</h3>
          <p className="text-xs text-gray-500 mb-2">Real-world status of all requests</p>
          <div className="h-48 flex justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={lifecycleCounts} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} fill="#8884d8" label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                  {lifecycleCounts.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={LIFECYCLE_COLORS[entry.name] || '#999'} />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{fontSize: '12px'}} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI Planning Outcome */}
        <div className="bg-white p-5 rounded-lg shadow-sm border border-rail-border">
          <h3 className="text-sm font-bold text-gray-800 mb-1">AI Planning Decisions</h3>
          <p className="text-xs text-gray-500 mb-2">CP-SAT optimizer results (excludes completed tasks)</p>
          <div className="h-48 flex justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={planningCounts} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} fill="#8884d8" label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                  {planningCounts.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PLANNING_COLORS[entry.name] || '#999'} />
                  ))}
                </Pie>
                <RechartsTooltip contentStyle={{fontSize: '12px'}} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Resource Demand */}
        <div className="bg-white p-5 rounded-lg shadow-sm border border-rail-border lg:col-span-2">
          <h3 className="text-sm font-bold text-gray-800 mb-1 flex items-center gap-1"><Layers className="w-4 h-4"/> Resource Demand</h3>
          <p className="text-xs text-gray-500 mb-4">Active tasks grouped by required maintenance resource</p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={resourceStats} margin={{ top: 10, right: 10, left: 10, bottom: 0 }} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{fontSize: 10}} />
                <YAxis dataKey="name" type="category" width={150} tick={{fontSize: 10}} />
                <RechartsTooltip cursor={{fill: '#f3f4f6'}} contentStyle={{fontSize: '12px'}} />
                <Bar dataKey="Demand" fill="#f59e0b" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
