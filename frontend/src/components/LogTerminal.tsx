import React, { useEffect, useRef } from 'react';
import type { LogEntry } from '../types';
import { Terminal } from 'lucide-react';
import clsx from 'clsx';

interface LogTerminalProps {
  logs: LogEntry[];
}

const LogTerminal: React.FC<LogTerminalProps> = ({ logs }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when logs change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="bg-zinc-900 rounded-md border border-zinc-800 overflow-hidden flex flex-col h-[400px]">
      <div className="bg-zinc-950 px-3 py-2 border-b border-zinc-800 flex items-center gap-2">
        <Terminal size={12} className="text-zinc-600" />
        <span className="text-zinc-500 text-[10px] uppercase tracking-wider font-medium">Console</span>
      </div>
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto font-mono text-xs"
      >
        {logs.length === 0 && (
          <div className="p-3 text-zinc-600">Waiting for events...</div>
        )}
        {logs.map((log, idx) => (
          <div 
            key={log.id} 
            className={clsx(
              "flex gap-3 px-3 py-1.5 border-b border-zinc-800/50",
              idx % 2 === 0 ? "bg-zinc-900" : "bg-zinc-950"
            )}
          >
            <span className="text-zinc-600 shrink-0 text-[10px]">{log.timestamp}</span>
            <span className={clsx(
              "break-all",
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
