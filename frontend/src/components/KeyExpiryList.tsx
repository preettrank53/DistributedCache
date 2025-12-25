import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, Database } from 'lucide-react';

interface KeyData {
  key: string;
  value: string;
  ttl_remaining: number | null;
  node: string;
}

const KeyExpiryList: React.FC = () => {
  const [keys, setKeys] = useState<KeyData[]>([]);
  const [lastUpdate, setLastUpdate] = useState<number>(Date.now());

  useEffect(() => {
    const fetchKeys = async () => {
      try {
        const response = await axios.get('http://127.0.0.1:8000/debug/keys');
        setKeys(response.data.keys || []);
        setLastUpdate(Date.now());
      } catch (error) {
        console.error('Failed to fetch keys:', error);
      }
    };

    // Initial fetch
    fetchKeys();

    // Poll every 1 second
    const interval = setInterval(fetchKeys, 1000);

    return () => clearInterval(interval);
  }, []);

  // Calculate time elapsed since last update for progress calculation
  const getProgress = (key: KeyData, now: number): number => {
    if (key.ttl_remaining === null) return 100; // No expiry
    
    // Calculate time elapsed since last fetch
    const elapsed = (now - lastUpdate) / 1000;
    const currentTTL = Math.max(0, key.ttl_remaining - elapsed);
    
    // Assume original TTL was 60 seconds max for percentage calculation
    // In reality, we'd need to track the original TTL
    const percentage = (currentTTL / 60) * 100;
    return Math.max(0, Math.min(100, percentage));
  };

  const getColorClass = (key: KeyData, now: number): string => {
    if (key.ttl_remaining === null) return 'bg-zinc-500'; // No expiry
    
    const elapsed = (now - lastUpdate) / 1000;
    const currentTTL = Math.max(0, key.ttl_remaining - elapsed);
    
    if (currentTTL > 10) return 'bg-emerald-500';
    if (currentTTL > 3) return 'bg-amber-500';
    return 'bg-red-500';
  };

  const shouldPulse = (key: KeyData, now: number): boolean => {
    if (key.ttl_remaining === null) return false;
    const elapsed = (now - lastUpdate) / 1000;
    const currentTTL = Math.max(0, key.ttl_remaining - elapsed);
    return currentTTL < 3;
  };

  const getCurrentTTL = (key: KeyData, now: number): number => {
    if (key.ttl_remaining === null) return 0;
    const elapsed = (now - lastUpdate) / 1000;
    return Math.max(0, key.ttl_remaining - elapsed);
  };

  // For real-time updates
  const [now, setNow] = useState(Date.now());
  
  useEffect(() => {
    const timer = setInterval(() => {
      setNow(Date.now());
    }, 100); // Update every 100ms for smooth animation
    
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="bg-zinc-900 rounded-md border border-zinc-800 p-5 h-full flex flex-col max-h-[600px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Clock size={16} className="text-zinc-500" />
          <h3 className="text-[10px] uppercase tracking-widest text-zinc-500 font-medium">
            Live Expiry Tracker
          </h3>
        </div>
        <div className="text-xs text-zinc-600 font-mono">
          {keys.length} {keys.length === 1 ? 'key' : 'keys'}
        </div>
      </div>

      {/* Keys List - Fixed Height with Scroll */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-2 min-h-0 custom-scrollbar" style={{ maxHeight: 'calc(600px - 120px)' }}>
        <AnimatePresence mode="popLayout">
          {keys.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-full text-zinc-600"
            >
              <Database size={32} className="mb-2 opacity-30" />
              <p className="text-xs">No active keys</p>
            </motion.div>
          ) : (
            keys.map((keyData) => {
              const currentTTL = getCurrentTTL(keyData, now);
              const progress = getProgress(keyData, now);
              const colorClass = getColorClass(keyData, now);
              const pulse = shouldPulse(keyData, now);

              return (
                <motion.div
                  key={keyData.key}
                  layout
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20, transition: { duration: 0.2 } }}
                  className="bg-zinc-950/50 rounded-md p-3 border border-zinc-800 hover:border-zinc-700 transition-colors"
                >
                  {/* Key Info */}
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-mono text-zinc-200 truncate">
                        {keyData.key}
                      </div>
                      <div className="text-[10px] text-zinc-600 truncate mt-0.5">
                        {keyData.value}
                      </div>
                    </div>
                    <div className="flex flex-col items-end ml-2">
                      <div className={`text-xs font-mono font-semibold ${
                        keyData.ttl_remaining === null 
                          ? 'text-zinc-500' 
                          : currentTTL > 10 
                            ? 'text-emerald-400' 
                            : currentTTL > 3 
                              ? 'text-amber-400' 
                              : 'text-red-400'
                      }`}>
                        {keyData.ttl_remaining === null ? '∞' : `${currentTTL.toFixed(1)}s`}
                      </div>
                      <div className="text-[9px] text-zinc-600 mt-0.5">
                        node:{keyData.node}
                      </div>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {keyData.ttl_remaining !== null && (
                    <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                      <motion.div
                        className={`h-full ${colorClass} ${pulse ? 'animate-pulse' : ''}`}
                        initial={{ width: '100%' }}
                        animate={{ width: `${progress}%` }}
                        transition={{ duration: 0.1, ease: 'linear' }}
                      />
                    </div>
                  )}
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
      </div>

      {/* Legend */}
      <div className="flex gap-3 mt-4 pt-3 border-t border-zinc-800 flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
          <span className="text-[9px] text-zinc-500">High (&gt;10s)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
          <span className="text-[9px] text-zinc-500">Medium (&lt;10s)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
          <span className="text-[9px] text-zinc-500">Critical (&lt;3s)</span>
        </div>
      </div>
      
      {/* Custom Scrollbar Styles */}
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #18181b;
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #3f3f46;
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #52525b;
        }
      `}</style>
    </div>
  );
};

export default KeyExpiryList;
