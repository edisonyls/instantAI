import React, { useState, useEffect } from "react";
import {
  Settings as SettingsIcon,
  Server,
  Database,
  Brain,
  RefreshCw,
  Download,
  CheckCircle,
  Loader2,
  Trash2,
} from "lucide-react";
import {
  getHealthStatus,
  HealthStatus,
  getSystemInfo,
  SystemInfo,
  startBackgroundPull,
  listActivePulls,
  deleteModel,
} from "../services/api";
import { showToast } from "../components/ui/Toaster";

export const Settings: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [infoLoading, setInfoLoading] = useState(true);
  const [pullingModel, setPullingModel] = useState<string | null>(null);
  const [pullProgress, setPullProgress] = useState<Record<string, string>>({});
  const [pullPercents, setPullPercents] = useState<Record<string, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [infoError, setInfoError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Note: Per-agent settings are edited on the agent page. Global overrides removed from here.

  const fetchHealthStatus = async () => {
    try {
      setLoading(true);
      const status = await getHealthStatus();
      setHealthStatus(status);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch health status"
      );
    } finally {
      setLoading(false);
    }
  };

  const fetchSystemInfo = async () => {
    try {
      setInfoLoading(true);
      const info = await getSystemInfo();
      setSystemInfo(info);
      setInfoError(null);
    } catch (err) {
      setInfoError(
        err instanceof Error ? err.message : "Failed to fetch system info"
      );
    } finally {
      setInfoLoading(false);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      await Promise.all([fetchHealthStatus(), fetchSystemInfo()]);
    };
    loadData();
  }, []);

  // On mount, resume/poll any active pulls so progress survives refresh
  useEffect(() => {
    let timer: number | undefined;
    const poll = async () => {
      try {
        const { active } = await listActivePulls();
        setPullProgress((prev) => {
          const next = { ...prev };
          Object.values(active || {}).forEach((st) => {
            next[st.model] = st.message || st.state;
          });
          return next;
        });
        // update percents
        setPullPercents(() => {
          const next: Record<string, number> = {};
          Object.values(active || {}).forEach((st: any) => {
            if (typeof st.percent === "number") {
              next[st.model] = Math.max(
                0,
                Math.min(100, Math.round(st.percent))
              );
            }
          });
          return next;
        });
      } catch {}
      timer = window.setTimeout(poll, 1500);
    };
    poll();
    return () => {
      if (timer) window.clearTimeout(timer);
    };
  }, []);

  const refreshAll = async () => {
    setRefreshing(true);
    try {
      await Promise.all([fetchHealthStatus(), fetchSystemInfo()]);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">System Info</h1>
          <p className="text-gray-600 mt-1">
            View current system configuration and health status
          </p>
        </div>
        <button
          onClick={refreshAll}
          disabled={refreshing}
          className={`btn btn-outline btn-sm flex items-center space-x-2 ${
            refreshing ? "opacity-75 cursor-not-allowed" : ""
          }`}
        >
          <RefreshCw
            className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
          />
          <span>{refreshing ? "Refreshing..." : "Refresh All"}</span>
        </button>
      </div>

      {/* System Health */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Server className="w-5 h-5 mr-2" />
          System Health
        </h2>

        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="loading-spinner"></div>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
          </div>
        ) : healthStatus ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-700">Overall Status</span>
              <span
                className={`px-2 py-1 rounded-full text-xs font-medium ${
                  healthStatus.status === "healthy"
                    ? "bg-green-100 text-green-800"
                    : "bg-red-100 text-red-800"
                }`}
              >
                {healthStatus.status}
              </span>
            </div>

            {healthStatus.services && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-900">
                  Service Status
                </h3>
                {Object.entries(healthStatus.services).map(
                  ([service, status]) => (
                    <div
                      key={service}
                      className="flex items-center justify-between"
                    >
                      <span className="text-gray-600 capitalize">
                        {service}
                      </span>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          status === "healthy" || status.status === "healthy"
                            ? "bg-green-100 text-green-800"
                            : status === "model_downloading"
                              ? "bg-yellow-100 text-yellow-800"
                              : "bg-red-100 text-red-800"
                        }`}
                      >
                        {typeof status === "string"
                          ? status === "model_downloading"
                            ? "Model Downloading..."
                            : status
                          : status.status}
                      </span>
                    </div>
                  )
                )}
              </div>
            )}

            <div className="text-xs text-gray-500">
              Last updated: {new Date(healthStatus.timestamp).toLocaleString()}
            </div>
          </div>
        ) : null}
      </div>

      {/* AI Configuration */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Brain className="w-5 h-5 mr-2" />
          AI Configuration
        </h2>

        {infoLoading ? (
          <div className="flex items-center justify-center h-24">
            <div className="loading-spinner"></div>
          </div>
        ) : infoError ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{infoError}</p>
          </div>
        ) : systemInfo ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Current Ollama Model
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.ai_configuration.ollama_model}
                </p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Model Status
                </label>
                <div className="flex items-center space-x-2">
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${
                      systemInfo.ai_configuration.model_ready
                        ? "bg-green-100 text-green-800"
                        : systemInfo.ai_configuration.ollama_status ===
                            "model_not_ready"
                          ? "bg-yellow-100 text-yellow-800"
                          : "bg-red-100 text-red-800"
                    }`}
                  >
                    {systemInfo.ai_configuration.model_ready
                      ? "Ready"
                      : systemInfo.ai_configuration.ollama_status ===
                          "model_not_ready"
                        ? "Downloading..."
                        : "Error"}
                  </span>
                  {!systemInfo.ai_configuration.model_ready &&
                    systemInfo.ai_configuration.ollama_status ===
                      "model_not_ready" && (
                      <span className="text-xs text-gray-500">
                        Model is being downloaded
                      </span>
                    )}
                </div>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ollama Host
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.ai_configuration.ollama_host}
                </p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Context Length
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.ai_configuration.max_context_length.toLocaleString()}{" "}
                  characters
                </p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Embedding Model
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.ai_configuration.embedding_model}
                </p>
              </div>
            </div>

            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-900 mb-2">
                Manage Models
              </h3>
              <div className="bg-gray-50 p-4 rounded-lg space-y-4">
                {/* Search and custom pull */}
                <div className="flex flex-col md:flex-row md:items-center md:space-x-3 space-y-2 md:space-y-0">
                  <input
                    type="text"
                    placeholder="Search or enter a model name (e.g., gemma3:4b)"
                    className="input flex-1"
                    onKeyDown={async (e) => {
                      const target = e.target as HTMLInputElement;
                      const name = target.value.trim();
                      if (e.key === "Enter" && name) {
                        try {
                          setPullingModel(name);
                          setPullProgress((p) => ({
                            ...p,
                            [name]: "Starting...",
                          }));
                          await startBackgroundPull(name);
                          setPullProgress((p) => ({
                            ...p,
                            [name]: "Starting...",
                          }));
                          setPullingModel(null);
                          setTimeout(fetchSystemInfo, 2000);
                        } catch {
                          setPullProgress((p) => ({ ...p, [name]: "Error" }));
                          setPullingModel(null);
                          alert(`Failed to download ${name}`);
                        }
                      }
                    }}
                  />
                  <span className="text-xs text-gray-500">
                    Press Enter to download
                  </span>
                </div>

                {/* Popular models list with installed markers */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-800">
                      Popular Models
                    </span>
                    <span className="text-xs text-gray-500">
                      Scroll to see more
                    </span>
                  </div>
                  <div className="max-h-56 overflow-auto divide-y divide-gray-200 bg-white rounded border">
                    {[
                      "gemma3:4b",
                      "gemma3:1b",
                      "gemma2:2b",
                      "qwen3:4b",
                      "qwen2.5:3b",
                      "llama3.2:1b",
                      "llama3.2:3b",
                      "mistral:7b",
                      "phi3:mini",
                    ].map((m) => {
                      const installed =
                        systemInfo?.ai_configuration?.available_models?.includes(
                          m
                        );
                      return (
                        <div
                          key={m}
                          className="flex items-center justify-between p-2"
                        >
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-sm text-gray-800">
                              {m}
                            </span>
                            {installed && (
                              <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">
                                Installed
                              </span>
                            )}
                          </div>
                          <div className="flex items-center space-x-2">
                            {pullingModel === m ||
                            (pullProgress[m] &&
                              pullProgress[m] !== "Completed" &&
                              pullProgress[m] !== "Error") ? (
                              <div className="flex items-center space-x-2">
                                <button
                                  aria-label="Downloading"
                                  disabled
                                  className="p-1.5 rounded text-gray-400"
                                >
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                </button>
                                <div className="w-24">
                                  <div className="h-1.5 bg-gray-200 rounded">
                                    <div
                                      className="h-1.5 bg-blue-600 rounded"
                                      style={{
                                        width: `${pullPercents[m] ?? 0}%`,
                                      }}
                                    />
                                  </div>
                                  <div className="text-[10px] text-gray-600 text-right">
                                    {pullPercents[m] ?? 0}%
                                  </div>
                                </div>
                              </div>
                            ) : installed ? (
                              <div className="flex items-center space-x-2">
                                <CheckCircle
                                  className="w-4 h-4 text-green-600"
                                  aria-hidden="true"
                                />
                                <button
                                  aria-label={`Delete ${m}`}
                                  title="Delete"
                                  className="p-1.5 rounded hover:bg-red-50 text-red-600"
                                  onClick={async () => {
                                    try {
                                      await deleteModel(m);
                                      await fetchSystemInfo();
                                      showToast(
                                        `Model ${m} has been deleted`,
                                        "success"
                                      );
                                    } catch (e) {
                                      showToast(
                                        `Failed to delete ${m}`,
                                        "error"
                                      );
                                    }
                                  }}
                                >
                                  <Trash2 className="w-4 h-4" />
                                  <span className="sr-only">Delete</span>
                                </button>
                              </div>
                            ) : (
                              <button
                                aria-label={`Download ${m}`}
                                title="Download"
                                className="p-1.5 rounded hover:bg-blue-50 text-blue-600"
                                onClick={async () => {
                                  try {
                                    setPullingModel(m);
                                    setPullProgress((p) => ({
                                      ...p,
                                      [m]: "Starting...",
                                    }));
                                    await startBackgroundPull(m);
                                    setPullProgress((p) => ({
                                      ...p,
                                      [m]: "Starting...",
                                    }));
                                    setPullingModel(null);
                                    setTimeout(fetchSystemInfo, 2000);
                                  } catch (e) {
                                    setPullProgress((p) => ({
                                      ...p,
                                      [m]: "Error",
                                    }));
                                    setPullingModel(null);
                                    // eslint-disable-next-line no-alert
                                    alert(`Failed to download ${m}`);
                                  }
                                }}
                              >
                                <Download className="w-4 h-4" />
                                <span className="sr-only">Download</span>
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Live progress */}
                {Object.keys(pullProgress).length > 0 && (
                  <div className="mt-2 space-y-1">
                    {Object.entries(pullProgress).map(([model, msg]) => (
                      <div key={model} className="text-xs text-gray-600">
                        <span className="font-mono mr-2">{model}</span>
                        <span>{msg}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Document Processing */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Database className="w-5 h-5 mr-2" />
          Document Processing
        </h2>

        {infoLoading ? (
          <div className="flex items-center justify-center h-24">
            <div className="loading-spinner"></div>
          </div>
        ) : infoError ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{infoError}</p>
          </div>
        ) : systemInfo ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Chunk Size
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.document_processing.chunk_size.toLocaleString()}{" "}
                  characters
                </p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Chunk Overlap
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.document_processing.chunk_overlap.toLocaleString()}{" "}
                  characters
                </p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max File Size
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.document_processing.max_file_size_mb} MB
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Storage Configuration */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <SettingsIcon className="w-5 h-5 mr-2" />
          Storage Configuration
        </h2>

        {infoLoading ? (
          <div className="flex items-center justify-center h-24">
            <div className="loading-spinner"></div>
          </div>
        ) : infoError ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{infoError}</p>
          </div>
        ) : systemInfo ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Upload Directory
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.storage.upload_directory}
                </p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Temporary Directory
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.storage.temp_directory}
                </p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ChromaDB Path
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.storage.chroma_db_path}
                </p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Vector DB Collection
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.storage.vector_db_collection}
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Security & Logging */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Server className="w-5 h-5 mr-2" />
          Security & Logging
        </h2>

        {infoLoading ? (
          <div className="flex items-center justify-center h-24">
            <div className="loading-spinner"></div>
          </div>
        ) : infoError ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{infoError}</p>
          </div>
        ) : systemInfo ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Token Expiry
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.security.access_token_expire_minutes} minutes
                </p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Log Level
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.logging.log_level}
                </p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Log File
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.logging.log_file}
                </p>
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  CORS Origins
                </label>
                <div className="space-y-1">
                  {systemInfo.security.cors_origins.map((origin, index) => (
                    <p key={index} className="text-gray-900 font-mono text-sm">
                      {origin}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* Info Note */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-blue-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">
              System Configuration
            </h3>
            <p className="mt-1 text-sm text-blue-700">
              Some settings can be modified directly through this interface
              (look for the edit icon), while others require updating the
              configuration file or environment variables and restarting the
              backend service.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
