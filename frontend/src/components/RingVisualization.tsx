import React from 'react';
import { motion } from 'framer-motion';
import type { Node } from '../types';

interface RingVisualizationProps {
  nodes: Node[];
  replicationPath?: string[]; // List of node IDs to highlight
}

const RingVisualization: React.FC<RingVisualizationProps> = ({ nodes, replicationPath = [] }) => {
  const radius = 140;
  const center = 200;
  const labelRadius = 175; // Distance for labels

  const getCoords = (angle: number) => {
    const angleInRadians = (angle - 90) * (Math.PI / 180);
    return {
      x: center + radius * Math.cos(angleInRadians),
      y: center + radius * Math.sin(angleInRadians)
    };
  };

  const getLabelCoords = (angle: number) => {
    const angleInRadians = (angle - 90) * (Math.PI / 180);
    return {
      x: center + labelRadius * Math.cos(angleInRadians),
      y: center + labelRadius * Math.sin(angleInRadians)
    };
  };

  // Group nodes by physical ID to get unique physical nodes
  const physicalNodes = Array.from(new Set(nodes.map(n => n.id))).map(id => {
    const nodeGroup = nodes.filter(n => n.id === id);
    const avgAngle = nodeGroup.reduce((sum, n) => sum + n.angle, 0) / nodeGroup.length;
    return { id, angle: avgAngle };
  });

  return (
    <div className="bg-zinc-900 rounded-md border border-zinc-800 p-8 h-[500px] flex items-center justify-center">
      <div className="relative w-[400px] h-[400px]">
        <svg width="400" height="400" className="absolute top-0 left-0">
          {/* Main Ring - Thin, crisp line */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="#3f3f46" // zinc-700
            strokeWidth="1"
          />
          
          {/* Replication Chords (Connecting Lines) */}
          {replicationPath.length > 1 && (() => {
            const activeNodes = physicalNodes.filter(p => replicationPath.includes(p.id));
            // Sort by angle for clean polygon
            activeNodes.sort((a, b) => a.angle - b.angle);
            
            return activeNodes.map((node, i) => {
              const nextNode = activeNodes[(i + 1) % activeNodes.length];
              const start = getCoords(node.angle);
              const end = getCoords(nextNode.angle);
              
              return (
                <motion.line
                  key={`chord-${i}`}
                  x1={start.x}
                  y1={start.y}
                  x2={end.x}
                  y2={end.y}
                  stroke="#10b981"
                  strokeWidth="1.5"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 0.6 }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                />
              );
            });
          })()}

          {/* Virtual Nodes - Tiny gray dots */}
          {nodes.map((node) => {
            const { x, y } = getCoords(node.angle);
            return (
              <circle
                key={`virtual-${node.id}-${node.angle}`}
                cx={x}
                cy={y}
                r="2"
                fill="#52525b" // zinc-600
              />
            );
          })}

          {/* Physical Nodes - Larger dots */}
          {physicalNodes.map((node) => {
            const { x, y } = getCoords(node.angle);
            const { x: labelX, y: labelY } = getLabelCoords(node.angle);
            const isTarget = replicationPath.includes(node.id);

            return (
              <motion.g key={`physical-${node.id}`}>
                {/* Node circle */}
                <motion.circle
                  cx={x}
                  cy={y}
                  r={isTarget ? "7" : "5"}
                  fill={isTarget ? "#10b981" : "#3b82f6"}
                  stroke="#ffffff"
                  strokeWidth="1.5"
                  initial={{ scale: 0 }}
                  animate={{ scale: isTarget ? 1.2 : 1 }}
                  transition={{ duration: 0.2 }}
                />
                
                {/* Label - Always horizontal */}
                <text
                  x={labelX}
                  y={labelY}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill={isTarget ? "#10b981" : "#a1a1aa"} // zinc-400
                  fontSize="11"
                  fontWeight={isTarget ? "600" : "400"}
                  fontFamily="monospace"
                  className="pointer-events-none"
                >
                  {node.id.split(':').pop()}
                </text>
                
                {/* Connector line from node to label */}
                <line
                  x1={x}
                  y1={y}
                  x2={labelX}
                  y2={labelY}
                  stroke="#3f3f46"
                  strokeWidth="0.5"
                  strokeDasharray="1,1"
                  opacity="0.3"
                />
              </motion.g>
            );
          })}
        </svg>
        
        {/* Center Label */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <div className="text-[10px] uppercase tracking-widest text-zinc-600 font-medium">Consistent Hash</div>
            <div className="text-xs text-zinc-500 font-mono mt-0.5">
              {replicationPath.length > 0 ? `→ ${replicationPath.length} Replicas` : `${physicalNodes.length} Nodes`}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RingVisualization;
