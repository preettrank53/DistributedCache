export interface Node {
  id: string;
  angle: number;
}

export interface LogEntry {
  id: number;
  timestamp: string;
  message: string;
  type: 'info' | 'success' | 'error';
}

export interface ClusterStats {
  ring_stats: {
    num_physical_nodes: number;
    num_virtual_nodes: number;
  };
  node_stats: Record<string, {
    hits: number;
    misses: number;
    hit_rate: number;
    current_size: number;
    capacity: number;
    error?: string;
  }>;
}
