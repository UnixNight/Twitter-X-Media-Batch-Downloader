import { useState, useEffect, useRef } from "react";
import { Trash2, Copy, Check, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { logger, type LogEntry } from "@/lib/logger";
import { GetDebugLogs } from "../../wailsjs/go/main/App";

const levelColors: Record<string, string> = {
  info: "text-blue-500",
  success: "text-green-500",
  warning: "text-yellow-500",
  error: "text-red-500",
  debug: "text-gray-500",
};

function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function DebugLoggerPage() {
  const [frontendLogs, setFrontendLogs] = useState<LogEntry[]>([]);
  const [backendLogs, setBackendLogs] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"frontend" | "backend">("frontend");
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Subscribe to frontend logs
  useEffect(() => {
    const unsubscribe = logger.subscribe(() => {
      setFrontendLogs(logger.getLogs());
    });
    setFrontendLogs(logger.getLogs());
    return () => {
      unsubscribe();
    };
  }, []);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [frontendLogs, backendLogs, activeTab]);

  // Fetch backend logs
  const fetchBackendLogs = async () => {
    setLoading(true);
    try {
      const logs = await GetDebugLogs(100);
      setBackendLogs(logs);
    } catch (error) {
      setBackendLogs(`Error fetching logs: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  // Load backend logs on component mount
  useEffect(() => {
    fetchBackendLogs();
  }, []);

  const handleClear = () => {
    if (activeTab === "frontend") {
      logger.clear();
    }
  };

  const handleCopy = async () => {
    let logText = "";
    
    if (activeTab === "frontend") {
      logText = frontendLogs
        .map((log) => `[${formatTime(log.timestamp)}] [${log.level}] ${log.message}`)
        .join("\n");
    } else {
      logText = backendLogs;
    }
    
    try {
      await navigator.clipboard.writeText(logText);
      setCopied(true);
      setTimeout(() => setCopied(false), 500);
    } catch (err) {
      console.error("Failed to copy logs:", err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Debug Logs</h1>
        <div className="flex items-center gap-2">
          {activeTab === "backend" && (
            <Button
              variant="outline"
              size="sm"
              onClick={fetchBackendLogs}
              disabled={loading}
              className="gap-1.5"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            disabled={(activeTab === "frontend" && frontendLogs.length === 0) || (activeTab === "backend" && !backendLogs)}
            className="gap-1.5"
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            Copy
          </Button>
          {activeTab === "frontend" && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleClear}
              className="gap-1.5"
            >
              <Trash2 className="h-4 w-4" />
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Tab buttons */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab("frontend")}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === "frontend"
              ? "border-b-2 border-blue-500 text-blue-500"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Frontend Logs
        </button>
        <button
          onClick={() => setActiveTab("backend")}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === "backend"
              ? "border-b-2 border-blue-500 text-blue-500"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Extractor Logs
        </button>
      </div>

      {/* Log display */}
      <div
        ref={scrollRef}
        className="h-[calc(100vh-320px)] overflow-y-auto bg-muted/50 rounded-md p-3 font-mono text-xs"
      >
        {activeTab === "frontend" ? (
          frontendLogs.length === 0 ? (
            <p className="text-muted-foreground lowercase">no frontend logs yet...</p>
          ) : (
            frontendLogs.map((log, i) => (
              <div key={i} className="flex gap-2 py-0.5">
                <span className="text-muted-foreground shrink-0">
                  [{formatTime(log.timestamp)}]
                </span>
                <span className={`shrink-0 w-16 ${levelColors[log.level]}`}>
                  [{log.level}]
                </span>
                <span className="break-all">{log.message}</span>
              </div>
            ))
          )
        ) : (
          backendLogs ? (
            <pre className="whitespace-pre-wrap break-words text-xs">{backendLogs}</pre>
          ) : (
            <p className="text-muted-foreground lowercase">no extractor logs yet...</p>
          )
        )}
      </div>
    </div>
  );
}
