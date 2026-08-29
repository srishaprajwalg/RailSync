import { useState, useEffect } from 'react';
import { fetchCorridor, fetchTimetables, fetchTasks, optimizeBlocks } from '../services/api';
import KPICards from './KPICards';
import BlockPlan from './BlockPlan';
import CorridorTimeline from './CorridorTimeline';
import TaskTable from './TaskTable';
import { Train, Activity, AlertTriangle } from 'lucide-react';

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [data, setData] = useState({
    corridor: [],
    timetables: [],
    tasks: [],
    blocks: [],
    metrics: null,
  });
  const [error, setError] = useState(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const [corridor, timetables, tasks] = await Promise.all([
        fetchCorridor(),
        fetchTimetables(),
        fetchTasks(),
      ]);
      setData(prev => ({ ...prev, corridor, timetables, tasks }));
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleOptimize = async () => {
    try {
      setOptimizing(true);
      const result = await optimizeBlocks();
      setData(prev => ({
        ...prev,
        blocks: result.blocks,
        metrics: result.metrics,
      }));
      setOptimizing(false);
    } catch (err) {
      setError(err.message);
      setOptimizing(false);
    }
  };

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-rail-blue">Loading simulator data...</div>;
  }

  return (
    <div className="min-h-screen bg-rail-bg">
      {/* Header */}
      <header className="bg-rail-blue text-white py-4 px-6 shadow-md">
        <div className="flex justify-between items-center max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <Train className="w-8 h-8 text-rail-saffron" />
            <div>
              <h1 className="text-xl font-bold tracking-tight">RailSync</h1>
              <p className="text-xs text-rail-border opacity-80">Automatic Block Planning System</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-semibold">Bengaluru City (SBC) → Jolarpettai (JTJ)</div>
            <div className="text-xs text-rail-saffron bg-white/10 px-2 py-0.5 rounded inline-block mt-1">Prototype Simulation</div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 px-6 space-y-6">
        {error && (
          <div className="bg-rail-error/10 border-l-4 border-rail-error text-rail-error p-4 flex gap-2">
            <AlertTriangle className="w-5 h-5" />
            {error}
          </div>
        )}

        {/* Prototype Disclaimer */}
        <div className="text-xs text-rail-text-muted bg-white px-4 py-2 border border-rail-border rounded-md shadow-sm">
          <strong>Note:</strong> Corridor, timetable, and maintenance data are simulated/approximate and are not actual Indian Railways operational data.
        </div>

        <div className="flex justify-between items-end">
          <div>
            <h2 className="text-2xl font-bold text-rail-text-dark">Maintenance Block Plan</h2>
            <p className="text-rail-text-muted text-sm">Coordinating multi-department requests with CP-SAT constraints</p>
          </div>
          <button 
            onClick={handleOptimize}
            disabled={optimizing}
            className={`px-6 py-2.5 rounded shadow-sm text-white font-medium flex items-center gap-2 transition-colors ${
              optimizing ? 'bg-rail-blue/70 cursor-not-allowed' : 'bg-rail-blue hover:bg-rail-blue/90'
            }`}
          >
            <Activity className="w-4 h-4" />
            {optimizing ? 'Running CP-SAT Solver...' : 'Generate Optimal Plan'}
          </button>
        </div>

        {data.metrics && <KPICards metrics={data.metrics} />}

        {data.blocks.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <CorridorTimeline corridor={data.corridor} timetables={data.timetables} blocks={data.blocks} />
            </div>
            <div className="lg:col-span-1">
              <BlockPlan blocks={data.blocks} tasks={data.tasks} />
            </div>
          </div>
        )}

        <div className="mt-8">
          <TaskTable tasks={data.tasks} blocks={data.blocks} />
        </div>
      </main>
    </div>
  );
}
