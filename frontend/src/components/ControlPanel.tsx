import React, { useState } from 'react';
import axios from 'axios';
import { Plus, Trash2, Save, Search, Activity, Skull, Zap } from 'lucide-react';

interface ControlPanelProps {
  onLog: (message: string, type: 'info' | 'success' | 'error') => void;
  onRefresh: () => void;
  onDataSaved: (nodes: string[]) => void;
  isSimulating: boolean;
  onToggleSimulation: (enabled: boolean) => void;
  isChaosMode: boolean;
  onToggleChaos: (enabled: boolean) => void;
  isCacheEnabled: boolean;
  onToggleCache: (enabled: boolean) => void;
}

const ControlPanel: React.FC<ControlPanelProps> = ({ 
  onLog, 
  onRefresh, 
  onDataSaved, 
  isSimulating, 
  onToggleSimulation, 
  isChaosMode, 
  onToggleChaos,
  isCacheEnabled,
  onToggleCache
}) => {
  const [addPort, setAddPort] = useState('8004');
  const [removePort, setRemovePort] = useState('');
  const [dataKey, setDataKey] = useState('');
  const [dataValue, setDataValue] = useState('');
  const [ttl, setTtl] = useState(20); // Default TTL: 20 seconds
  const [getKey, setGetKey] = useState('');

  const API_URL = 'http://127.0.0.1:8000';

  const handleAddNode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addPort) return;

    try {
      onLog(`Adding node on port ${addPort}...`, 'info');
      await axios.post(`${API_URL}/cluster/add-node`, {
        port: parseInt(addPort),
        host: '127.0.0.1'
      });
      onLog(`Node ${addPort} added successfully!`, 'success');
      onRefresh();
      setAddPort((prev) => (parseInt(prev) + 1).toString());
    } catch (error: any) {
      console.error("Add Node Error:", error);
      const errorMessage = error.response?.data?.detail || error.message || "Unknown error";
      onLog(`Failed to add node: ${errorMessage}`, 'error');
    }
  };

  const handleRemoveNode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!removePort) return;

    try {
      onLog(`Removing node on port ${removePort}...`, 'info');
      await axios.delete(`${API_URL}/cluster/remove-node/${removePort}`);
      onLog(`Node ${removePort} removed successfully!`, 'success');
      onRefresh();
      setRemovePort('');
    } catch (error: any) {
      onLog(`Failed to remove node: ${error.response?.data?.detail || error.message}`, 'error');
    }
  };

  const handleSaveData = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dataKey || !dataValue) return;

    try {
      onLog(`Saving key '${dataKey}' with TTL=${ttl}s...`, 'info');
      const response = await axios.post(`${API_URL}/data`, {
        key: dataKey,
        value: dataValue,
        ttl: ttl
      });
      
      const nodes = response.data.nodes || [];
      onLog(`Saved! Replicated to ${nodes.length} nodes (TTL: ${ttl}s)`, 'success');
      onDataSaved(nodes);
      
      setDataKey('');
      setDataValue('');
    } catch (error: any) {
      onLog(`Failed to save data: ${error.response?.data?.detail || error.message}`, 'error');
    }
  };

  const handleGetData = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!getKey) return;

    try {
      onLog(`Fetching key '${getKey}'...`, 'info');
      const response = await axios.get(`${API_URL}/data/${getKey}`);
      onLog(`HIT! Value: "${response.data.value}" (Source: ${response.data.source})`, 'success');
    } catch (error: any) {
      if (error.response?.status === 404) {
        onLog(`MISS! Key '${getKey}' not found`, 'error');
      } else {
        onLog(`Error fetching data: ${error.response?.data?.detail || error.message}`, 'error');
      }
    }
  };

  const [activeTab, setActiveTab] = useState<'cluster' | 'data' | 'traffic' | 'chaos'>('cluster');

  return (
    <div className="bg-zinc-900 rounded-md border border-zinc-800 p-5 h-full">
      {/* Segmented Control Tabs */}
      <div className="flex gap-1 bg-zinc-800 rounded-md p-1 mb-5">
        <button
          onClick={() => setActiveTab('cluster')}
          className={`flex-1 px-3 py-1.5 rounded text-xs font-medium transition-all ${
            activeTab === 'cluster'
              ? 'bg-zinc-900 text-white shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Cluster
        </button>
        <button
          onClick={() => setActiveTab('data')}
          className={`flex-1 px-3 py-1.5 rounded text-xs font-medium transition-all ${
            activeTab === 'data'
              ? 'bg-zinc-900 text-white shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Data Ops
        </button>
        <button
          onClick={() => setActiveTab('traffic')}
          className={`flex-1 px-3 py-1.5 rounded text-xs font-medium transition-all ${
            activeTab === 'traffic'
              ? 'bg-zinc-900 text-white shadow-sm'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Traffic
        </button>
        <button
          onClick={() => setActiveTab('chaos')}
          className={`flex-1 px-3 py-1.5 rounded text-xs font-medium transition-all ${
            activeTab === 'chaos'
              ? 'bg-zinc-900 text-white shadow-sm'
              : isChaosMode 
              ? 'text-red-500 hover:text-red-400 animate-pulse'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          Chaos
        </button>
      </div>

      {activeTab === 'cluster' && (
        <div className="space-y-4">
          {/* Add Node */}
          <form onSubmit={handleAddNode} className="space-y-2">
            <label className="block text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
              Add Node
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                placeholder="8004"
                value={addPort}
                onChange={(e) => setAddPort(e.target.value)}
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-blue-500 transition-shadow"
              />
              <button
                type="submit"
                className="bg-white text-black px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-200 transition-colors flex items-center gap-1.5"
              >
                <Plus size={14} /> Add
              </button>
            </div>
          </form>

          {/* Remove Node */}
          <form onSubmit={handleRemoveNode} className="space-y-2">
            <label className="block text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
              Remove Node
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                placeholder="Port"
                value={removePort}
                onChange={(e) => setRemovePort(e.target.value)}
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-red-500 transition-shadow"
              />
              <button
                type="submit"
                className="bg-red-500/10 text-red-500 px-4 py-2 rounded-md text-sm font-medium hover:bg-red-500/20 transition-colors flex items-center gap-1.5"
              >
                <Trash2 size={14} /> Remove
              </button>
            </div>
          </form>
        </div>
      )}

      {activeTab === 'traffic' && (
        <div className="space-y-4">
          {/* Traffic Simulator */}
          <div className="p-6 bg-zinc-950/50 rounded-lg border border-zinc-800 flex flex-col items-center justify-center space-y-4">
            <div className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${
              isSimulating ? 'bg-blue-500/20 text-blue-400 animate-pulse' : 'bg-zinc-800 text-zinc-500'
            }`}>
              <Activity size={28} />
            </div>
            <div className="text-center">
              <h3 className="text-sm font-medium text-zinc-200">Traffic Simulator</h3>
              <p className="text-xs text-zinc-500 mt-1">Generates random GET/PUT traffic</p>
            </div>
            <button
              onClick={() => onToggleSimulation(!isSimulating)}
              className={`w-full py-2.5 px-4 rounded-md text-sm font-medium transition-all ${
                isSimulating 
                  ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20' 
                  : 'bg-blue-500 text-white hover:bg-blue-600'
              }`}
            >
              {isSimulating ? 'Stop Simulation' : 'Start Simulation'}
            </button>
            {isSimulating && (
              <div className="text-xs text-zinc-500 font-mono text-center">
                <span className="inline-block w-2 h-2 bg-emerald-500 rounded-full animate-pulse mr-2"></span>
                Active • 5 req/s
              </div>
            )}
          </div>

          {/* Performance Demo - Cache Bypass */}
          <div className="p-6 bg-zinc-950/50 rounded-lg border border-zinc-800 flex flex-col items-center justify-center space-y-4">
            <div className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${
              isCacheEnabled ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
            }`}>
              <Zap size={28} />
            </div>
            <div className="text-center">
              <h3 className="text-sm font-medium text-zinc-200">Performance Demo</h3>
              <p className="text-xs text-zinc-500 mt-1">
                {isCacheEnabled ? 'Cache enabled (~10ms latency)' : 'Cache bypassed (~300ms latency)'}
              </p>
            </div>
            <button
              onClick={() => onToggleCache(!isCacheEnabled)}
              className={`w-full py-2.5 px-4 rounded-md text-sm font-medium transition-all ${
                isCacheEnabled 
                  ? 'bg-emerald-500 text-white hover:bg-emerald-600' 
                  : 'bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 border border-amber-500/20'
              }`}
            >
              {isCacheEnabled ? 'Cache Enabled' : 'Database Direct Mode'}
            </button>
            <div className="text-xs text-zinc-500 text-center">
              Toggle to demonstrate cache performance vs. direct database access
            </div>
          </div>
        </div>
      )}

      {activeTab === 'chaos' && (
        <div className="space-y-4">
          {/* Danger Zone Header */}
          <div className="border border-red-900/30 rounded-lg p-4 bg-red-950/10">
            <div className="flex items-center gap-2 mb-2">
              <Skull size={18} className="text-red-500" />
              <h3 className="text-sm font-semibold text-red-400 uppercase tracking-wider">Danger Zone</h3>
            </div>
            <p className="text-xs text-zinc-500">
              Resilience testing mode. Randomly terminates cache nodes to demonstrate fault tolerance.
            </p>
          </div>

          {/* Chaos Monkey Control */}
          <div className="p-6 bg-zinc-950/50 rounded-lg border-2 border-red-900/30 flex flex-col items-center justify-center space-y-4">
            <div className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${
              isChaosMode 
                ? 'bg-red-600/30 text-red-400 animate-pulse shadow-lg shadow-red-500/30' 
                : 'bg-zinc-800 text-red-700 border-2 border-red-900'
            }`}>
              <Skull size={32} />
            </div>
            <div className="text-center">
              <h3 className="text-sm font-medium text-zinc-200">Chaos Monkey</h3>
              <p className="text-xs text-zinc-500 mt-1">
                {isChaosMode ? 'Actively destroying nodes...' : 'Fault tolerance testing'}
              </p>
            </div>
            <button
              onClick={() => onToggleChaos(!isChaosMode)}
              className={`w-full py-2.5 px-4 rounded-md text-sm font-semibold transition-all ${
                isChaosMode 
                  ? 'bg-red-600 text-white hover:bg-red-700 shadow-lg shadow-red-500/50 animate-pulse' 
                  : 'bg-zinc-900 text-red-500 hover:bg-red-950 border-2 border-red-900 hover:border-red-700'
              }`}
            >
              {isChaosMode ? '🛑 Stop Chaos' : '💀 Unleash Chaos'}
            </button>
            {isChaosMode && (
              <div className="text-xs text-red-500 font-mono text-center font-semibold">
                <span className="inline-block w-2 h-2 bg-red-500 rounded-full animate-pulse mr-2"></span>
                CHAOS ACTIVE • Kills every 5-8s
              </div>
            )}
            {!isChaosMode && (
              <div className="text-[10px] text-zinc-600 text-center">
                Requires 4+ nodes to start
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'data' && (
        <div className="space-y-4">
          {/* Write Data */}
          <form onSubmit={handleSaveData} className="space-y-2">
            <label className="block text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
              Write Key-Value
            </label>
            <input
              type="text"
              placeholder="key"
              value={dataKey}
              onChange={(e) => setDataKey(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-shadow"
            />
            <input
              type="text"
              placeholder="value"
              value={dataValue}
              onChange={(e) => setDataValue(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-700 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-shadow"
            />
            
            {/* TTL Slider */}
            <div className="pt-2">
              <div className="flex justify-between items-center mb-2">
                <label className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
                  Time to Live
                </label>
                <span className="text-sm font-mono text-emerald-400">{ttl}s</span>
              </div>
              <input
                type="range"
                min="5"
                max="60"
                value={ttl}
                onChange={(e) => setTtl(parseInt(e.target.value))}
                className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
              />
              <div className="flex justify-between text-[9px] text-zinc-600 mt-1">
                <span>5s</span>
                <span>60s</span>
              </div>
            </div>
            
            <button
              type="submit"
              className="w-full bg-emerald-500/10 text-emerald-400 px-4 py-2 rounded-md text-sm font-medium hover:bg-emerald-500/20 transition-colors flex items-center justify-center gap-1.5"
            >
              <Save size={14} /> Save
            </button>
          </form>

          <div className="border-t border-zinc-800"></div>

          {/* Read Data */}
          <form onSubmit={handleGetData} className="space-y-2">
            <label className="block text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
              Read Key
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="key"
                value={getKey}
                onChange={(e) => setGetKey(e.target.value)}
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-md px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-blue-500 transition-shadow"
              />
              <button
                type="submit"
                className="bg-blue-500/10 text-blue-400 px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-500/20 transition-colors flex items-center gap-1.5"
              >
                <Search size={14} /> Get
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

export default ControlPanel;
