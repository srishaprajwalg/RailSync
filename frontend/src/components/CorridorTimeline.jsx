import { useMemo, useState } from 'react';
import { formatTime } from '../utils/formatters';

export default function CorridorTimeline({ corridor, timetables, blocks }) {
  const [selectedDirection, setSelectedDirection] = useState('Up');
  
  // SVG Coordinates setup
  const width = 800;
  const height = 500;
  const paddingX = 60;
  const paddingY = 40;
  
  const graphWidth = width - 2 * paddingX;
  const graphHeight = height - 2 * paddingY;
  
  const maxChainage = Math.max(...corridor.map(c => c.chainage_km));
  const minChainage = Math.min(...corridor.map(c => c.chainage_km));
  
  const getY = (km) => paddingY + ((km - minChainage) / (maxChainage - minChainage)) * graphHeight;
  const getX = (mins) => paddingX + (mins / 1440) * graphWidth;
  
  const filteredSchedules = useMemo(() => timetables.filter(t => t.direction === selectedDirection), [timetables, selectedDirection]);
  const filteredBlocks = useMemo(() => blocks.filter(b => b.line_direction === selectedDirection), [blocks, selectedDirection]);

  // Hours for grid
  const hours = Array.from({length: 25}, (_, i) => i * 60);

  return (
    <div className="bg-white border border-rail-border rounded-lg shadow-sm">
      <div className="p-4 border-b border-rail-border bg-rail-bg/50 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold text-rail-text-dark">Time-Distance Visualization</h3>
          <p className="text-xs text-rail-text-muted">Train movements and scheduled blocks</p>
        </div>
        <div className="flex bg-gray-100 rounded p-1">
          <button 
            className={`px-3 py-1 text-sm font-medium rounded ${selectedDirection === 'Up' ? 'bg-white shadow text-rail-blue' : 'text-gray-500 hover:text-gray-700'}`}
            onClick={() => setSelectedDirection('Up')}
          >
            Up Line
          </button>
          <button 
            className={`px-3 py-1 text-sm font-medium rounded ${selectedDirection === 'Down' ? 'bg-white shadow text-rail-blue' : 'text-gray-500 hover:text-gray-700'}`}
            onClick={() => setSelectedDirection('Down')}
          >
            Down Line
          </button>
        </div>
      </div>
      
      <div className="p-4 overflow-x-auto">
        <svg width="100%" height="500" viewBox={`0 0 ${width} ${height}`} className="font-sans">
          
          {/* X Axis Grid (Time) */}
          {hours.map((mins) => (
            <g key={mins}>
              <line x1={getX(mins)} y1={paddingY} x2={getX(mins)} y2={height - paddingY} stroke="#E2E8F0" strokeWidth="1" strokeDasharray="4,4" />
              {mins % 120 === 0 && (
                <text x={getX(mins)} y={height - paddingY + 20} fontSize="10" fill="#64748B" textAnchor="middle">
                  {formatTime(mins)}
                </text>
              )}
            </g>
          ))}
          
          {/* Y Axis Grid (Stations) */}
          {corridor.map((station) => (
            <g key={station.id}>
              <line x1={paddingX} y1={getY(station.chainage_km)} x2={width - paddingX} y2={getY(station.chainage_km)} stroke="#E2E8F0" strokeWidth="1" />
              <text x={paddingX - 10} y={getY(station.chainage_km) + 3} fontSize="10" fill="#17202A" textAnchor="end" fontWeight="500">
                {station.id}
              </text>
            </g>
          ))}

          {/* Train Paths */}
          {filteredSchedules.map((train, i) => {
            const points = train.stops.map(stop => {
              const station = corridor.find(c => c.id === stop.station_id);
              if (!station) return '';
              // Approximating continuous movement between arrival and departure
              // For a time-distance graph, we usually just connect arrival/departure points.
              return `${getX(stop.arrival_mins)},${getY(station.chainage_km)} ${getX(stop.departure_mins)},${getY(station.chainage_km)}`;
            }).join(' ');
            
            return (
              <polyline key={train.train_id} points={points} fill="none" stroke="#0B3A5B" strokeWidth="1.5" opacity="0.6" />
            );
          })}

          {/* Maintenance Blocks */}
          {filteredBlocks.map((block) => {
            const x1 = getX(block.start_time_mins);
            const w = getX(block.end_time_mins) - x1;
            const y1 = getY(block.start_km);
            const h = getY(block.end_km) - y1;
            
            // h could be negative if Down line (higher km to lower km), handle standard rect coordinates
            const rectY = Math.min(y1, y1 + h);
            const rectH = Math.abs(h);
            
            return (
              <g key={block.id}>
                <rect 
                  x={x1} 
                  y={rectY} 
                  width={w} 
                  height={rectH || 5} // If it's a point task, give it 5px height
                  fill="#F28C28" 
                  fillOpacity="0.7" 
                  stroke="#D97706" 
                  strokeWidth="1"
                  rx="2"
                />
                <text x={x1 + w/2} y={rectY + rectH/2 + 3} fontSize="9" fill="white" textAnchor="middle" fontWeight="bold">
                  {block.assigned_tasks.length > 1 ? 'CONS' : 'BLK'}
                </text>
              </g>
            );
          })}
          
        </svg>
        
        {/* Legend */}
        <div className="flex justify-center gap-6 mt-2 text-xs text-rail-text-muted">
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 bg-rail-blue inline-block"></span> Train Movement
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-rail-saffron/70 border border-rail-warning rounded-sm inline-block"></span> Maintenance Block
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 border border-rail-border rounded-sm inline-block"></span> Station Line
          </div>
        </div>
      </div>
    </div>
  );
}
