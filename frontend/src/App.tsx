import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import type { Node, LogEntry } from './types';
import RingVisualization from './components/RingVisualization';
import ControlPanel from './components/ControlPanel';
import LogTerminal from './components/LogTerminal';
import MetricsChart from './components/MetricsChart';
import KeyExpiryList from './components/KeyExpiryList';
import { Server } from 'lucide-react';

function App() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [partitions, setPartitions] = useState<Array<{ source: string; target: string }>>([]);
  
  // Enhanced Stats State
  const [globalStats, setGlobalStats] = useState({
    hitRate: 0,
    totalRequests: 0,
    nodeLoad: [] as Array<{ name: string; keys: number }>,
    requestDistribution: [] as Array<{ name: string; value: number }>
  });
  const [trafficHistory, setTrafficHistory] = useState<Array<{ time: string; hits: number; misses: number }>>([]);
  const [latencyHistory, setLatencyHistory] = useState<Array<{ time: string; latency: number }>>([]);
  const lastStatsRef = useRef({ hits: 0, misses: 0 });
  
  const [replicationPath, setReplicationPath] = useState<string[]>([]);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isChaosMode, setIsChaosMode] = useState(false);
  const [isCacheEnabled, setIsCacheEnabled] = useState(true);

  const addLog = useCallback((message: string, type: 'info' | 'success' | 'error' = 'info') => {
    setLogs((prev) => [
      ...prev,
      {
        id: Date.now(),
        timestamp: new Date().toLocaleTimeString(),
        message,
        type
      }
    ]);
  }, []);

  const fetchClusterMap = useCallback(async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8000/cluster/map');
      setNodes(response.data.nodes);
    } catch (error) {
      console.error('Failed to fetch cluster map:', error);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8000/stats/global');
      const data = response.data;
      
      const currentHits = data.request_distribution.find((d: any) => d.name === 'Hits')?.value || 0;
      const currentMisses = data.request_distribution.find((d: any) => d.name === 'Misses')?.value || 0;
      
      // Calculate deltas for traffic chart
      const deltaHits = Math.max(0, currentHits - lastStatsRef.current.hits);
      const deltaMisses = Math.max(0, currentMisses - lastStatsRef.current.misses);
      
      lastStatsRef.current = { hits: currentHits, misses: currentMisses };
      
      setGlobalStats({
        hitRate: data.hit_rate,
        totalRequests: data.total_requests,
        nodeLoad: data.node_load,
        requestDistribution: data.request_distribution
      });
      
      // Update traffic history
      setTrafficHistory(prev => {
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const newPoint = { time: timeStr, hits: deltaHits, misses: deltaMisses };
        const updated = [...prev, newPoint];
        return updated.length > 20 ? updated.slice(-20) : updated;
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  }, []);

  // Traffic Simulator
  useEffect(() => {
    if (!isSimulating) return;

    const interval = setInterval(async () => {
      const isWrite = Math.random() > 0.7; // 70% reads, 30% writes
      const key = `user_${Math.floor(Math.random() * 100)}`;
      
      try {
        if (isWrite) {
          const value = `session_${Date.now()}`;
          // Random TTL between 10-30 seconds for realistic simulation
          const ttl = Math.floor(Math.random() * 21) + 10; // 10-30 seconds
          await axios.post('http://127.0.0.1:8000/data', { key, value, ttl });
        } else {
          const startTime = performance.now();
          const response = await axios.get(`http://127.0.0.1:8000/data/${key}?bypass_cache=${!isCacheEnabled}`);
          const endTime = performance.now();
          
          // Track latency from response or measure client-side
          const latency = response.data.latency_ms || (endTime - startTime);
          
          setLatencyHistory(prev => {
            const now = new Date();
            const timeStr = now.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const newPoint = { time: timeStr, latency: Math.round(latency) };
            const updated = [...prev, newPoint];
            return updated.length > 30 ? updated.slice(-30) : updated;
          });
        }
      } catch {
        // Ignore errors (404 misses throw errors in axios)
      }
    }, 200); // 5 requests per second

    return () => clearInterval(interval);
  }, [isSimulating, isCacheEnabled]);

  // Chaos Mode Handler
  const handleToggleChaos = useCallback(async (enabled: boolean) => {
    try {
      if (enabled) {
        const response = await axios.post('http://127.0.0.1:8000/chaos/start');
        setIsChaosMode(true);
        addLog('CHAOS MODE ACTIVATED - Nodes will be randomly terminated', 'error');
        addLog(response.data.message, 'info');
      } else {
        const response = await axios.post('http://127.0.0.1:8000/chaos/stop');
        setIsChaosMode(false);
        addLog('Chaos Mode deactivated - System stabilized', 'success');
        addLog(response.data.message, 'info');
      }
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to toggle chaos mode';
      addLog(`Chaos Mode Error: ${errorMsg}`, 'error');
      setIsChaosMode(false);
    }
  }, [addLog]);

  // Cache Toggle Handler
  const handleToggleCache = useCallback((enabled: boolean) => {
    setIsCacheEnabled(enabled);
    if (enabled) {
      addLog('Cache enabled - Fast mode (~10ms latency)', 'success');
    } else {
      addLog('Cache bypassed - Database direct mode (~300ms latency)', 'info');
    }
  }, [addLog]);

  // Fetch partition list
  const fetchPartitions = useCallback(async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8000/partition/list');
      setPartitions(response.data.partitions || []);
    } catch (error) {
      console.error('Failed to fetch partitions:', error);
    }
  }, []);

  // Toggle partition between two nodes
  const handlePartitionToggle = useCallback(async (sourcePort: string, targetPort: string) => {
    try {
      // Check if partition already exists
      const exists = partitions.some(
        p => (p.source === sourcePort && p.target === targetPort) || 
             (p.source === targetPort && p.target === sourcePort)
      );

      if (exists) {
        // Remove partition
        await axios.post('http://127.0.0.1:8000/partition/remove', null, {
          params: { source_port: sourcePort, target_port: targetPort }
        });
        addLog(`⚡ Network partition REMOVED: ${sourcePort} <--> ${targetPort}`, 'success');
      } else {
        // Create partition
        await axios.post('http://127.0.0.1:8000/partition/create', null, {
          params: { source_port: sourcePort, target_port: targetPort }
        });
        addLog(`⚡ Network partition CREATED: ${sourcePort} <--X--> ${targetPort}`, 'error');
      }

      // Refresh partition list
      await fetchPartitions();
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to toggle partition';
      addLog(`Partition Error: ${errorMsg}`, 'error');
    }
  }, [partitions, addLog, fetchPartitions]);

  const handleDataSaved = (nodes: string[]) => {
    setReplicationPath(nodes);
    // Clear the path after 3 seconds
    setTimeout(() => setReplicationPath([]), 3000);
  };

  // Initial fetch and polling
  useEffect(() => {
    fetchClusterMap();
    fetchStats();
    fetchPartitions();
    addLog('Dashboard initialized. Connecting to Load Balancer...', 'info');

    const interval = setInterval(() => {
        fetchClusterMap();
        fetchStats();
        fetchPartitions();
    }, 2000);
    return () => clearInterval(interval);
  }, [fetchClusterMap, fetchStats, fetchPartitions, addLog]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6 font-sans">
      <div className="max-w-7xl mx-auto space-y-4">
        {/* Header */}
        <header className="flex items-center justify-between pb-4 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-white rounded-md flex items-center justify-center">
              <Server size={18} className="text-black" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-white">DistriCache</h1>
              <p className="text-xs text-zinc-500">System / Cluster-1</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs text-zinc-400">
            <span className="font-mono">{nodes.length} Virtual Nodes</span>
            <span className="font-mono">{globalStats.totalRequests} Requests</span>
            {isSimulating && (
              <span className="flex items-center gap-1 text-blue-400">
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                Simulating
              </span>
            )}
            {isChaosMode && (
              <span className="flex items-center gap-1 text-red-500 font-semibold">
                <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                CHAOS MODE
              </span>
            )}
            {!isCacheEnabled && (
              <span className="flex items-center gap-1 text-amber-500 font-semibold">
                <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse"></span>
                SLOW MODE
              </span>
            )}
          </div>
        </header>
              
        {/* Bento Grid Layout */}
        <div className="grid grid-cols-12 gap-4">
          {/* Ring Visualization - Large */}
          <div className="col-span-12 lg:col-span-8">
            <RingVisualization 
              nodes={nodes} 
              replicationPath={replicationPath} 
              partitions={partitions}
              onPartitionToggle={handlePartitionToggle}
            />
          </div>

          {/* Metrics - Small */}
          <div className="col-span-12 lg:col-span-4">
            <MetricsChart 
              nodeLoad={globalStats.nodeLoad}
              trafficHistory={trafficHistory}
              latencyHistory={latencyHistory}
              hitRate={globalStats.hitRate}
              totalRequests={globalStats.totalRequests}
            />
          </div>

          {/* Control Panel - Medium */}
          <div className="col-span-12 lg:col-span-4">
            <ControlPanel 
              onLog={addLog} 
              onRefresh={fetchClusterMap} 
              onDataSaved={handleDataSaved}
              isSimulating={isSimulating}
              onToggleSimulation={setIsSimulating}
              isChaosMode={isChaosMode}
              onToggleChaos={handleToggleChaos}
              isCacheEnabled={isCacheEnabled}
              onToggleCache={handleToggleCache}
            />
          </div>

          {/* Key Expiry Tracker - Medium */}
          <div className="col-span-12 lg:col-span-4 h-[600px]">
            <KeyExpiryList />
          </div>

          {/* Logs - Medium */}
          <div className="col-span-12 lg:col-span-4">
            <LogTerminal logs={logs} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
