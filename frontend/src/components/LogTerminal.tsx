import React, { useEffect, useRef, useState } from 'react';
import type { LogEntry } from '../types';
import { Terminal, Maximize2, Minimize2 } from 'lucide-react';
import clsx from 'clsx';

interface LogTerminalProps {
  logs: LogEntry[];
}

const LogTerminal: React.FC<LogTerminalProps> = ({ logs }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  // Auto-scroll to bottom when logs change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div 
      className={clsx(
        "bg-zinc-900 rounded-md border border-zinc-800 overflow-hidden flex flex-col transition-all duration-300",
        isExpanded 
          ? "fixed bottom-4 left-4 right-4 z-50 h-[80vh] shadow-2xl" 
          : "h-[400px]"
      )}
    >
      <div className="bg-zinc-950 px-3 py-2 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal size={12} className="text-zinc-600" />
          <span className="text-zinc-500 text-[10px] uppercase tracking-wider font-medium">Console</span>
          <span className="text-zinc-600 text-[10px]">({logs.length} entries)</span>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-zinc-500 hover:text-zinc-300 transition-colors p-1 hover:bg-zinc-800 rounded"
          title={isExpanded ? "Minimize" : "Expand"}
        >
          {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>
      </div>
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto font-mono text-[10px]"
      >
        {logs.length === 0 && (
          <div className="p-3 text-zinc-600">Waiting for events...</div>
        )}
        {logs.map((log, idx) => (
          <div 
            key={log.id} 
            className={clsx(
              "flex gap-3 px-3 py-1 border-b border-zinc-800/50",
              idx % 2 === 0 ? "bg-zinc-900" : "bg-zinc-950"
            )}
          >
            <span className="text-zinc-600 shrink-0 text-[9px]">{log.timestamp}</span>
            <span className={clsx(
              "break-all leading-relaxed",
              log.type === 'info' && "text-zinc-400",
              log.type === 'success' && "text-emerald-400",
              log.type === 'error' && "text-red-400"
            )}>
              {log.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LogTerminal;
