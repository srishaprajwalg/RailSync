import { useMemo, useState } from 'react';
import { formatTime } from '../utils/formatters';
import { Info } from 'lucide-react';

export default function CorridorTimeline({ corridor, timetables, forecasts, blocks, timeWindow }) {
  const [selectedDirection, setSelectedDirection] = useState('Up');

  // SVG Coordinates setup
  const width = 850;
  const height = 550;
  const paddingX = 80;
  const paddingY = 60;

  const graphWidth = width - paddingX * 2;
  const graphHeight = height - paddingY * 2;

  const maxChainage = Math.max(...corridor.map(c => c.chainage_km));
  const minChainage = Math.min(...corridor.map(c => c.chainage_km));

  const windowDuration = timeWindow.end - timeWindow.start;
  const getY = (km) => paddingY + ((km - minChainage) / (maxChainage - minChainage)) * graphHeight;
  const getX = (mins) => {
    // If the event starts before window but ends inside, or vice versa, still plot based on actual time
    return paddingX + ((mins - timeWindow.start) / windowDuration) * graphWidth;
  };

  const filteredSchedules = useMemo(() => timetables.filter(t => t.direction === selectedDirection), [timetables, selectedDirection]);
  const filteredForecasts = useMemo(() => forecasts?.filter(f => f.direction === selectedDirection) || [], [forecasts, selectedDirection]);
  const filteredBlocks = useMemo(() => blocks.filter(b => b.line_direction === selectedDirection), [blocks, selectedDirection]);

  // Intervals for grid based on window duration
  const getGridIntervals = () => {
    if (windowDuration <= 1440) {
      // Daily view: every hour
      const count = 25;
      return Array.from({length: count}, (_, i) => timeWindow.start + (i * 60));
    } else if (windowDuration <= 7 * 1440) {
      // Weekly view: every day
      const count = 8;
      return Array.from({length: count}, (_, i) => timeWindow.start + (i * 1440));
    } else {
      // Monthly view: every day
      const count = 31;
      return Array.from({length: count}, (_, i) => timeWindow.start + (i * 1440));
    }
  };
  const intervals = getGridIntervals();

  return (
    <div className="bg-white border border-rail-border rounded-lg shadow-sm">
      <div className="p-4 border-b border-gray-100 bg-gray-50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
            Time-Distance Visualization
            <span className="text-[10px] font-bold uppercase tracking-wider bg-green-100 text-green-800 px-2 py-0.5 rounded">
              Post-Optimization (Latest Plan)
            </span>
          </h3>
          <p className="text-xs text-gray-500 max-w-md mt-1">
            See exactly when and where trains are moving, and where maintenance blocks have been safely scheduled between them.
          </p>
        </div>

        {(() => {
          const parts = corridor?.code?.split('-') || ['Start', 'End'];
          const startStn = parts[0];
          const endStn = parts[1] || 'End';
          return (
            <div className="flex bg-gray-200 rounded p-1 shrink-0">
              <button
                className={`px-3 py-1.5 text-xs font-semibold rounded transition-colors ${selectedDirection === 'Up' ? 'bg-white shadow text-indigo-700' : 'text-gray-600 hover:text-gray-800'}`}
                onClick={() => setSelectedDirection('Up')}
              >
                Toward {endStn} (Up Line)
              </button>
              <button
                className={`px-3 py-1.5 text-xs font-semibold rounded transition-colors ${selectedDirection === 'Down' ? 'bg-white shadow text-fuchsia-700' : 'text-gray-600 hover:text-gray-800'}`}
                onClick={() => setSelectedDirection('Down')}
              >
                Toward {startStn} (Down Line)
              </button>
            </div>
          );
        })()}
      </div>

      {/* Visual Helper */}
      <div className="px-5 py-3 border-b border-gray-100 flex items-start gap-2 bg-blue-50/30">
        <Info className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
        <p className="text-[11px] text-gray-600">
          <strong>How to read this chart:</strong> Time moves from left to right. Distance moves from top to bottom.
          The diagonal lines are moving trains. The orange boxes are track areas reserved for maintenance.
          RailVyuha ensures the orange boxes never touch the train lines.
        </p>
      </div>

      <div className="p-4 overflow-x-auto">
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="font-sans">

          {/* Axis Labels */}
          <text x={width / 2} y={height - 15} fontSize="12" fontWeight="bold" fill="#4B5563" textAnchor="middle">
            Time (left to right) →
          </text>

          <text x="15" y={height / 2} fontSize="12" fontWeight="bold" fill="#4B5563" textAnchor="middle" transform={`rotate(-90 15 ${height/2})`}>
            Distance / Stations →
          </text>

          {/* X Axis Grid (Time) */}
          {intervals.map((mins) => {
            const isMajor = windowDuration <= 1440 ? mins % 120 === 0 : true;
            return (
              <g key={mins}>
                <line x1={getX(mins)} y1={paddingY} x2={getX(mins)} y2={height - paddingY} stroke="#f1f5f9" strokeWidth="1" strokeDasharray="4,4" />
                {isMajor && (
                  <text x={getX(mins)} y={height - paddingY + 20} fontSize="10" fill="#64748B" textAnchor="middle" fontWeight="500">
                    {windowDuration <= 1440 ? formatTime(mins, false) : `Day ${Math.floor(mins/1440)+1}`}
                  </text>
                )}
              </g>
            );
          })}

          {/* Y Axis Grid (Stations) */}
          {corridor.map((station) => (
            <g key={station.id}>
              <line x1={paddingX} y1={getY(station.chainage_km)} x2={width - paddingX} y2={getY(station.chainage_km)} stroke="#e2e8f0" strokeWidth="1" />
              <text x={paddingX - 10} y={getY(station.chainage_km) + 3} fontSize="10" fill="#475569" textAnchor="end" fontWeight="600">
                {station.name}
              </text>
              <text x={paddingX - 10} y={getY(station.chainage_km) + 14} fontSize="8" fill="#94a3b8" textAnchor="end">
                Km {station.chainage_km.toFixed(0)}
              </text>
            </g>
          ))}

          {/* Goods Train Forecast Windows */}
          {filteredForecasts.map((forecast) => {
            const totalDist = Math.abs(forecast.end_km - forecast.start_km);
            const nominalSpeedKmh = 40.0;
            const expectedTransitMins = Math.min(
               Math.floor((totalDist / nominalSpeedKmh) * 60),
               forecast.latest_exit_mins - forecast.earliest_entry_mins
            );

            const totalWindowMins = forecast.latest_exit_mins - forecast.earliest_entry_mins;
            const uncertaintyBufferMins = totalWindowMins - expectedTransitMins;
            const expectedCorridorEntry = forecast.earliest_entry_mins + Math.floor(uncertaintyBufferMins / 2);

            const yStart = getY(forecast.start_km);
            const yEnd = getY(forecast.end_km);

            const xExpectedStart = getX(expectedCorridorEntry);
            const xExpectedEnd = getX(expectedCorridorEntry + expectedTransitMins);

            const xEarliestStart = getX(expectedCorridorEntry - Math.floor(uncertaintyBufferMins / 2));
            const xLatestStart = getX(expectedCorridorEntry + Math.floor(uncertaintyBufferMins / 2));

            const xEarliestEnd = getX(expectedCorridorEntry + expectedTransitMins - Math.floor(uncertaintyBufferMins / 2));
            const xLatestEnd = getX(expectedCorridorEntry + expectedTransitMins + Math.floor(uncertaintyBufferMins / 2));

            const points = `${xEarliestStart},${yStart} ${xLatestStart},${yStart} ${xLatestEnd},${yEnd} ${xEarliestEnd},${yEnd}`;

            return (
              <g key={forecast.forecast_id}>
                <title>Expected freight movement with protected uncertainty safety window.</title>
                <polygon
                  points={points}
                  fill="#94a3b8"
                  fillOpacity="0.2"
                  stroke="#94a3b8"
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
                <line
                  x1={xExpectedStart} y1={yStart}
                  x2={xExpectedEnd} y2={yEnd}
                  stroke="#64748b" strokeWidth="1.5" strokeDasharray="4,4" opacity="0.8"
                />
              </g>
            );
          })}

          {/* Train Paths */}
          {filteredSchedules.map((train) => {
            const points = train.stops.map(stop => {
              const station = corridor.find(c => c.id === stop.station_id);
              if (!station) return '';
              return `${getX(stop.arrival_mins)},${getY(station.chainage_km)} ${getX(stop.departure_mins)},${getY(station.chainage_km)}`;
            }).join(' ');

            return (
              <g key={train.train_id}>
                <title>Passenger Train: {train.type} traveling {train.direction === 'Up' ? 'Toward End' : 'Toward Start'}.</title>
                <polyline points={points} fill="none" stroke="#0f172a" strokeWidth="1.5" opacity="0.6" />
              </g>
            );
          })}

          {/* Maintenance Blocks */}
          {filteredBlocks.map((block) => {
            const x1 = getX(block.start_time_mins);
            const w = Math.max(getX(block.end_time_mins) - x1, 2);
            const y1 = getY(block.start_km);
            const h = getY(block.end_km) - y1;

            const rectY = Math.min(y1, y1 + h);
            const rectH = Math.abs(h);
            const isPointTask = rectH < 5;

            return (
              <g key={block.id}>
                <title>Maintenance Block: Safe window reserved from {formatTime(block.start_time_mins)} to {formatTime(block.end_time_mins)} between Km {block.start_km.toFixed(1)} and {block.end_km.toFixed(1)}.</title>
                <rect
                  x={x1}
                  y={isPointTask ? rectY - 3 : rectY}
                  width={w}
                  height={isPointTask ? 6 : rectH}
                  fill="#f97316"
                  fillOpacity="0.8"
                  stroke="#c2410c"
                  strokeWidth="1"
                  rx="1"
                />
                {!isPointTask && rectH > 10 && w > 30 && (
                  <text
                    x={x1 + 4}
                    y={rectY + 12}
                    fontSize="9"
                    fill="#fff"
                    fontWeight="bold"
                    clipPath={`url(#clip-${block.id})`}
                  >
                    {block.assigned_tasks && block.assigned_tasks.length > 1 ? "Multi-Task" : "Task"}
                  </text>
                )}
                <defs>
                  <clipPath id={`clip-${block.id}`}>
                    <rect x={x1} y={isPointTask ? rectY - 3 : rectY} width={w} height={isPointTask ? 6 : rectH} />
                  </clipPath>
                </defs>
              </g>
            );
          })}

        </svg>

        {/* Legend */}
        <div className="flex justify-center gap-6 mt-2 pb-2 text-xs text-gray-600 font-medium bg-white">
          <div className="flex items-center gap-2">
            <span className="w-6 h-0.5 bg-[#0f172a] inline-block opacity-60"></span>
            <span>Passenger Train</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 bg-[#94a3b8] opacity-20 border border-slate-300 border-dashed inline-block"></span>
            <span>Freight Train Window</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 bg-orange-500 opacity-80 border border-orange-700 rounded-sm inline-block"></span>
            <span>Maintenance Block</span>
          </div>
        </div>
      </div>
    </div>
  );
}
