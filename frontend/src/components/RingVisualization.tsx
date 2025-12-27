import React from 'react';
import { motion } from 'framer-motion';
import type { Node } from '../types';

interface Partition {
  source: string;
  target: string;
}

interface RingVisualizationProps {
  nodes: Node[];
  replicationPath?: string[]; // List of node IDs to highlight
  partitions?: Partition[]; // List of network partitions
  onPartitionToggle?: (sourcePort: string, targetPort: string) => void; // Callback for partition toggle
}

const RingVisualization: React.FC<RingVisualizationProps> = ({ 
  nodes, 
  replicationPath = [], 
  partitions = [],
  onPartitionToggle 
}) => {
  const radius = 140;
  const center = 200;
  const labelRadius = 175; // Distance for labels
  const [selectedNode, setSelectedNode] = React.useState<string | null>(null);

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

  // Check if partition exists between two ports
  const hasPartition = (port1: string, port2: string): boolean => {
    return partitions.some(
      p => (p.source === port1 && p.target === port2) || (p.source === port2 && p.target === port1)
    );
  };

  // Handle click between nodes to toggle partition
  const handleLineClick = (node1: any, node2: any) => {
    if (!onPartitionToggle) return;
    
    const port1 = node1.id.split(':').pop();
    const port2 = node2.id.split(':').pop();
    onPartitionToggle(port1, port2);
  };

  // Handle node click for partition selection
  const handleNodeClick = (node: any) => {
    if (!onPartitionToggle) return;
    
    const port = node.id.split(':').pop();
    
    if (!selectedNode) {
      // First click - select this node
      setSelectedNode(port);
    } else if (selectedNode === port) {
      // Clicking same node - deselect
      setSelectedNode(null);
    } else {
      // Second click - create/remove partition between selected and this node
      onPartitionToggle(selectedNode, port);
      setSelectedNode(null);
    }
  };

  // Generate jagged lightning bolt path between two points
  const generateLightningPath = (x1: number, y1: number, x2: number, y2: number): string => {
    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2;
    const dx = x2 - x1;
    const dy = y2 - y1;
    const length = Math.sqrt(dx * dx + dy * dy);
    
    // Perpendicular offset for jagged effect
    const offsetX = -dy / length * 10;
    const offsetY = dx / length * 10;
    
    // Create zigzag points
    const p1x = x1 + dx * 0.25;
    const p1y = y1 + dy * 0.25;
    const p2x = midX + offsetX;
    const p2y = midY + offsetY;
    const p3x = x1 + dx * 0.75;
    const p3y = y1 + dy * 0.75;
    
    return `M ${x1},${y1} L ${p1x},${p1y} L ${p2x},${p2y} L ${p3x},${p3y} L ${x2},${y2}`;
  };

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
              const port1 = node.id.split(':').pop() || '';
              const port2 = nextNode.id.split(':').pop() || '';
              const isPartitioned = hasPartition(port1, port2);
              
              if (isPartitioned) {
                // Show failed replication with red X
                const midX = (start.x + end.x) / 2;
                const midY = (start.y + end.y) / 2;
                
                return (
                  <g key={`chord-${i}`}>
                    {/* Dashed line showing attempted replication */}
                    <motion.line
                      x1={start.x}
                      y1={start.y}
                      x2={end.x}
                      y2={end.y}
                      stroke="#ef4444"
                      strokeWidth="1.5"
                      strokeDasharray="5,5"
                      initial={{ pathLength: 0, opacity: 0 }}
                      animate={{ pathLength: 1, opacity: 0.6 }}
                      transition={{ duration: 0.5, ease: "easeOut" }}
                    />
                    {/* Red X marker */}
                    <g>
                      <circle cx={midX} cy={midY} r="8" fill="#ef4444" opacity="0.9" />
                      <text
                        x={midX}
                        y={midY + 1}
                        textAnchor="middle"
                        dominantBaseline="middle"
                        fill="#ffffff"
                        fontSize="12"
                        fontWeight="bold"
                      >
                        ✕
                      </text>
                    </g>
                  </g>
                );
              } else {
                // Normal successful replication
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
              }
            });
          })()}

          {/* Clickable Invisible Lines Between Adjacent Nodes for Partition Toggle */}
          {onPartitionToggle && physicalNodes.map((node, i) => {
            const nextNode = physicalNodes[(i + 1) % physicalNodes.length];
            const start = getCoords(node.angle);
            const end = getCoords(nextNode.angle);
            
            return (
              <line
                key={`clickable-${i}`}
                x1={start.x}
                y1={start.y}
                x2={end.x}
                y2={end.y}
                stroke="transparent"
                strokeWidth="20"
                style={{ cursor: 'pointer' }}
                onClick={() => handleLineClick(node, nextNode)}
                className="hover:stroke-red-500 hover:stroke-opacity-20 transition-all"
              />
            );
          })}

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
            const port = node.id.split(':').pop();
            const isSelected = selectedNode === port;

            return (
              <motion.g key={`physical-${node.id}`}>
                {/* Selection ring (when node is selected) */}
                {isSelected && (
                  <motion.circle
                    cx={x}
                    cy={y}
                    r="12"
                    fill="none"
                    stroke="#eab308"
                    strokeWidth="2"
                    strokeDasharray="3,3"
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.2 }}
                  />
                )}
                
                {/* Node circle */}
                <motion.circle
                  cx={x}
                  cy={y}
                  r={isTarget ? "7" : "5"}
                  fill={isSelected ? "#eab308" : (isTarget ? "#10b981" : "#3b82f6")}
                  stroke="#ffffff"
                  strokeWidth="1.5"
                  initial={{ scale: 0 }}
                  animate={{ scale: isTarget ? 1.2 : 1 }}
                  transition={{ duration: 0.2 }}
                  style={{ cursor: onPartitionToggle ? 'pointer' : 'default' }}
                  onClick={() => handleNodeClick(node)}
                  className={onPartitionToggle ? "hover:opacity-80" : ""}
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

          {/* Network Partition Lines (Lightning Bolts) - Drawn LAST to appear on top */}
          {partitions.map((partition, idx) => {
            const sourceNode = physicalNodes.find(n => n.id.includes(partition.source));
            const targetNode = physicalNodes.find(n => n.id.includes(partition.target));
            
            if (!sourceNode || !targetNode) return null;
            
            const start = getCoords(sourceNode.angle);
            const end = getCoords(targetNode.angle);
            const lightningPath = generateLightningPath(start.x, start.y, end.x, end.y);
            
            return (
              <motion.g 
                key={`partition-${idx}`}
                style={{ cursor: 'pointer' }}
                onClick={() => onPartitionToggle && onPartitionToggle(partition.source, partition.target)}
              >
                {/* Glow effect (drawn first, so it's behind the main line) */}
                <motion.path
                  d={lightningPath}
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity="0.4"
                  filter="blur(2px)"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.3 }}
                />
                {/* Main jagged red lightning bolt (on top) */}
                <motion.path
                  d={lightningPath}
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: 0.3 }}
                  style={{ filter: 'drop-shadow(0 0 4px rgba(239, 68, 68, 0.8))' }}
                  className="hover:brightness-125 transition-all"
                />
                {/* Invisible clickable area for easier clicking */}
                <path
                  d={lightningPath}
                  fill="none"
                  stroke="transparent"
                  strokeWidth="20"
                  strokeLinecap="round"
                />
              </motion.g>
            );
          })}
        </svg>
        
        {/* Center Label */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center">
            {selectedNode ? (
              <>
                <div className="text-[10px] uppercase tracking-widest text-yellow-500 font-medium">Node {selectedNode} Selected</div>
                <div className="text-xs text-yellow-400 font-mono mt-0.5">
                  Click another node to partition
                </div>
              </>
            ) : (
              <>
                <div className="text-[10px] uppercase tracking-widest text-zinc-600 font-medium">Consistent Hash</div>
                <div className="text-xs text-zinc-500 font-mono mt-0.5">
                  {replicationPath.length > 0 ? `→ ${replicationPath.length} Replicas` : `${physicalNodes.length} Nodes`}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RingVisualization;
