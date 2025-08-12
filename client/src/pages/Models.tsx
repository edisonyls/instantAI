import React, { useState, useEffect, useCallback } from "react";
import {
  Download,
  Trash2,
  AlertTriangle,
  Eye,
  RefreshCw,
  Loader2,
  X,
} from "lucide-react";
import { cn } from "../utils/cn";
import { showToast } from "../components/ui/Toaster";
// Note: We're using direct fetch calls instead of the API service functions
// to take advantage of the proxy configuration in the React development server

interface Agent {
  id: string;
  name: string;
  agent_type: string;
}

interface ModelInfo {
  name: string;
  is_system_default: boolean;
  in_use: boolean;
  usage_count: number;
  agents: Agent[];
}

export const Models: React.FC = () => {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pullModel, setPullModel] = useState("");
  const [isPulling, setIsPulling] = useState(false);

  const [showUsageModal, setShowUsageModal] = useState<ModelInfo | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(
    null
  );

  // Enhanced progress tracking states (from Settings page)
  const [pullProgress, setPullProgress] = useState<Record<string, string>>({});
  const [pullPercents, setPullPercents] = useState<Record<string, number>>({});
  const [verifyingModels, setVerifyingModels] = useState<Set<string>>(
    new Set()
  );
  const [cancellingModels, setCancellingModels] = useState<Set<string>>(
    new Set()
  );
  const [refreshTimeout, setRefreshTimeout] = useState<number | null>(null);

  const fetchModels = useCallback(async () => {
    try {
      const response = await fetch("/api/models");
      if (!response.ok) {
        throw new Error(
          `Failed to fetch models (${response.status}: ${response.statusText})`
        );
      }
      const data = await response.json();
      setModels(data.models || []);
      setError(null); // Clear any previous errors
    } catch (err) {
      console.error("Error fetching models:", err);
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch models";
      setError(
        `${errorMessage}. Please ensure the backend is running and accessible.`
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const updateAvailableModels = useCallback(async () => {
    try {
      await fetchModels(); // Refresh the models list
    } catch (err) {
      console.error("Failed to update available models:", err);
    }
  }, [fetchModels]);

  const debouncedRefreshModels = useCallback(() => {
    if (refreshTimeout) {
      clearTimeout(refreshTimeout);
    }

    const newTimeout = window.setTimeout(() => {
      updateAvailableModels();
      setRefreshTimeout(null);
    }, 1000);

    setRefreshTimeout(newTimeout);
  }, [refreshTimeout, updateAvailableModels]);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  // Enhanced polling system for progress tracking (from Settings page)
  useEffect(() => {
    let timer: number | undefined;
    const poll = async () => {
      try {
        const response = await fetch("/api/models/pull/active");
        if (!response.ok) return;
        const { active } = await response.json();

        // Debug logging
        if (Object.keys(active || {}).length > 0) {
          console.log("Active downloads:", active);
        }

        setPullProgress((prev) => {
          const next = { ...prev };
          Object.values(active || {}).forEach((st: any) => {
            next[st.model] = st.message || st.state;
          });
          return next;
        });

        setPullPercents((prevPercents) => {
          const next: Record<string, number> = { ...prevPercents };
          const activeSet = new Set<string>(
            Object.values(active || {}).map((st: any) => st.model)
          );
          const newVerifyingModels = new Set<string>();

          // Update active progress (never let percent go backwards; treat verifying as 100%)
          Object.values(active || {}).forEach((st: any) => {
            const prevVal = prevPercents[st.model] ?? 0;
            let incoming: number | null = null;
            if (typeof st.percent === "number") {
              incoming = Math.max(0, Math.min(100, Math.round(st.percent)));
            }

            // Check if this model is in verification phase
            const isVerifying =
              st.phase === "verifying" ||
              (() => {
                const message: string = (st.message || st.state || "")
                  .toString()
                  .toLowerCase();
                return (
                  message.includes("verify") ||
                  message.includes("sha256") ||
                  message.includes("digest")
                );
              })();

            if (isVerifying) {
              newVerifyingModels.add(st.model);
              next[st.model] = Math.max(prevVal, 100);
            } else if (incoming !== null) {
              next[st.model] = Math.max(prevVal, incoming);
            } else {
              if (prevVal > 0) next[st.model] = prevVal;
            }
          });

          // Update verifying state
          setVerifyingModels(newVerifyingModels);
          const completedNow: string[] = [];
          Object.keys(prevPercents).forEach((model) => {
            if (!activeSet.has(model)) {
              if (prevPercents[model] < 100) {
                completedNow.push(model);
              }
              delete next[model];
            }
          });

          // Check for completed models
          Object.values(active || {}).forEach((st: any) => {
            if (st.state === "completed" && st.phase === "completed") {
              if (
                !completedNow.includes(st.model) &&
                prevPercents[st.model] !== undefined
              ) {
                completedNow.push(st.model);
                delete next[st.model];
              }
            } else if (st.state === "cancelled") {
              if (prevPercents[st.model] !== undefined) {
                setPullProgress((p) => ({
                  ...p,
                  [st.model]: "Cancelled",
                }));
                delete next[st.model];
              }
            }
          });

          if (completedNow.length > 0) {
            setPullProgress((p) => {
              const np = { ...p };
              completedNow.forEach((m) => (np[m] = "Completed"));
              return np;
            });
            // Refresh models list after completion
            debouncedRefreshModels();
            showToast(
              `Model download completed: ${completedNow.join(", ")}`,
              "success"
            );
          }
          return next;
        });
      } catch (error) {
        console.error("Error polling pull status:", error);
      }
      timer = window.setTimeout(poll, 1500);
    };
    poll();
    return () => {
      if (timer) window.clearTimeout(timer);
      if (refreshTimeout) clearTimeout(refreshTimeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // We want this to run only once on mount

  useEffect(() => {
    return () => {
      if (refreshTimeout) clearTimeout(refreshTimeout);
    };
  }, [refreshTimeout]);

  const handlePullModel = async () => {
    if (!pullModel.trim()) return;

    const modelName = pullModel.trim();
    setIsPulling(true);
    try {
      setPullProgress((p) => ({
        ...p,
        [modelName]: "Starting...",
      }));

      const response = await fetch(
        `/api/models/pull/background?model=${encodeURIComponent(modelName)}`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to start download");
      }

      setPullModel("");
      showToast(`Started downloading ${modelName}`, "success");
      debouncedRefreshModels();
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to start download";
      setError(errorMessage);
      showToast(`Failed to start download: ${errorMessage}`, "error");
      setPullProgress((p) => ({
        ...p,
        [modelName]: "Error",
      }));
    } finally {
      setIsPulling(false);
    }
  };

  const confirmDeleteModel = (modelName: string) => {
    setShowDeleteConfirm(modelName);
  };

  const handleDeleteModel = async (modelName: string) => {
    setShowDeleteConfirm(null);

    try {
      const response = await fetch(
        `/api/models?model=${encodeURIComponent(modelName)}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        if (response.status === 409) {
          // Model is in use - show detailed error
          const detail = errorData.detail;
          if (typeof detail === "object" && detail.agents_using_model) {
            alert(
              `Cannot delete model "${modelName}":\n\n${detail.message}\n\nAgents using this model:\n${detail.agents_using_model.join("\n")}\n\n${detail.suggestion}`
            );
          } else {
            alert(detail.message || errorData.detail);
          }
          return;
        }
        throw new Error(errorData.detail || "Failed to delete model");
      }

      // Refresh models list
      fetchModels();
      showToast(`Model ${modelName} deleted successfully`, "success");
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to delete model";
      setError(errorMessage);
      showToast(`Failed to delete ${modelName}: ${errorMessage}`, "error");
    }
  };

  const handleCancelDownload = async (modelName: string) => {
    try {
      setCancellingModels((prev) => new Set(prev).add(modelName));
      const response = await fetch(
        `/api/models/pull?model=${encodeURIComponent(modelName)}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to cancel download");
      }

      setPullProgress((prev) => ({
        ...prev,
        [modelName]: "Cancelled",
      }));
      setPullPercents((prev) => {
        const next = { ...prev };
        delete next[modelName];
        return next;
      });
      setVerifyingModels((prev) => {
        const next = new Set(prev);
        next.delete(modelName);
        return next;
      });
      showToast(`Download of ${modelName} cancelled`, "success");
    } catch (error) {
      console.error("Failed to cancel download:", error);
      showToast(`Failed to cancel download of ${modelName}`, "error");
    } finally {
      setCancellingModels((prev) => {
        const next = new Set(prev);
        next.delete(modelName);
        return next;
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading models...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Model Management</h1>
        <button
          onClick={() => {
            setLoading(true);
            fetchModels();
          }}
          disabled={loading}
          className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
        >
          <RefreshCw
            className={cn("w-4 h-4 mr-2", loading && "animate-spin")}
          />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-2 text-sm text-red-700">{error}</div>
            </div>
          </div>
        </div>
      )}

      {/* Download New Model */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Download New Model
        </h2>
        <div className="flex space-x-4">
          <input
            type="text"
            value={pullModel}
            onChange={(e) => setPullModel(e.target.value)}
            placeholder="Enter model name (e.g., llama2, codellama, mistral)"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            onKeyPress={(e) => e.key === "Enter" && handlePullModel()}
          />
          <button
            onClick={handlePullModel}
            disabled={isPulling || !pullModel.trim()}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4 mr-2" />
            {isPulling ? "Starting..." : "Download"}
          </button>
        </div>
        <div className="mt-3 text-sm text-gray-500">
          <p className="font-medium mb-2">Available models to download:</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            <div>
              <strong>Small Models (1-3B params):</strong>
            </div>
            <div>• gemma2:2b (default)</div>
            <div>• gemma:2b</div>
            <div>• phi3:mini</div>
            <div>• phi3.5:3.8b</div>
            <div>• qwen2:1.5b</div>

            <div>
              <strong>Medium Models (7-8B params):</strong>
            </div>
            <div>• llama3.2:3b</div>
            <div>• llama3.1:8b</div>
            <div>• mistral:7b</div>
            <div>• gemma2:9b</div>
            <div>• qwen2.5:7b</div>

            <div>
              <strong>Large Models (13B+ params):</strong>
            </div>
            <div>• llama3.1:70b</div>
            <div>• llama3.2:11b</div>
            <div>• mistral:22b</div>
            <div>• qwen2.5:32b</div>
            <div>• deepseek-coder:6.7b</div>

            <div>
              <strong>Code Models:</strong>
            </div>
            <div>• codellama:7b</div>
            <div>• codellama:13b</div>
            <div>• codegeex4:9b</div>
            <div>• starcoder2:3b</div>
            <div>• deepseek-coder:1.3b</div>
          </div>
          <p className="mt-2 text-xs text-gray-400">
            Note: Larger models require more RAM and processing power but
            provide better quality responses.
          </p>
        </div>
      </div>

      {/* Live progress messages for models not yet in the table */}
      {Object.keys(pullProgress).length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-medium text-blue-800 mb-3">
            Download Activity
          </h3>
          <div className="space-y-3">
            {Object.entries(pullProgress)
              .filter(
                ([modelName]) => !models.some((m) => m.name === modelName)
              )
              .map(([modelName, message]) => (
                <div key={modelName} className="bg-white rounded-lg p-3 border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-sm font-medium text-gray-800">
                      {modelName}
                    </span>
                    <div className="flex items-center space-x-2">
                      {pullPercents[modelName] !== undefined && (
                        <span className="text-xs text-gray-600">
                          {verifyingModels.has(modelName)
                            ? "Verifying..."
                            : `${pullPercents[modelName] ?? 0}%`}
                        </span>
                      )}
                      <button
                        onClick={() => handleCancelDownload(modelName)}
                        disabled={cancellingModels.has(modelName)}
                        className={cn(
                          "p-1 rounded",
                          cancellingModels.has(modelName)
                            ? "text-gray-400 cursor-not-allowed"
                            : "text-red-600 hover:bg-red-50"
                        )}
                        title="Cancel download"
                      >
                        {cancellingModels.has(modelName) ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <X className="w-3 h-3" />
                        )}
                      </button>
                    </div>
                  </div>
                  {pullPercents[modelName] !== undefined && (
                    <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${pullPercents[modelName] ?? 0}%` }}
                      />
                    </div>
                  )}
                  <div className="text-xs text-gray-600">{message}</div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Installed Models */}
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            Installed Models
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Model Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Usage
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {models.map((model) => (
                <tr key={model.name} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {model.name}
                        </div>
                        {model.is_system_default && (
                          <div className="text-xs text-blue-600 font-medium">
                            System Default
                          </div>
                        )}
                        {/* Progress bar for downloading models */}
                        {pullProgress[model.name] &&
                          pullProgress[model.name] !== "Completed" &&
                          pullProgress[model.name] !== "Error" &&
                          pullProgress[model.name] !== "Cancelled" && (
                            <div className="mt-2">
                              <div className="flex items-center space-x-2">
                                <div className="w-32">
                                  <div className="h-1.5 bg-gray-200 rounded">
                                    <div
                                      className="h-1.5 bg-blue-600 rounded transition-all duration-300"
                                      style={{
                                        width: `${pullPercents[model.name] ?? 0}%`,
                                      }}
                                    />
                                  </div>
                                  <div className="text-[10px] text-gray-600 text-right">
                                    {verifyingModels.has(model.name)
                                      ? "Verifying..."
                                      : `${pullPercents[model.name] ?? 0}%`}
                                  </div>
                                </div>
                                <button
                                  onClick={() =>
                                    handleCancelDownload(model.name)
                                  }
                                  disabled={cancellingModels.has(model.name)}
                                  className={cn(
                                    "p-1 rounded",
                                    cancellingModels.has(model.name)
                                      ? "text-gray-400 cursor-not-allowed"
                                      : "text-red-600 hover:bg-red-50"
                                  )}
                                  title="Cancel download"
                                >
                                  {cancellingModels.has(model.name) ? (
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                  ) : (
                                    <X className="w-3 h-3" />
                                  )}
                                </button>
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                {pullProgress[model.name]}
                              </div>
                            </div>
                          )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={cn(
                        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                        model.in_use
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-800"
                      )}
                    >
                      {model.in_use ? "In Use" : "Available"}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div className="flex items-center space-x-2">
                      <span>{model.usage_count} agent(s)</span>
                      {model.usage_count > 0 && (
                        <button
                          onClick={() => setShowUsageModal(model)}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => confirmDeleteModel(model.name)}
                        disabled={model.is_system_default}
                        className={cn(
                          "inline-flex items-center px-3 py-1 border border-transparent text-sm leading-4 font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2",
                          model.is_system_default
                            ? "text-gray-400 cursor-not-allowed"
                            : model.in_use
                              ? "text-orange-700 bg-orange-100 hover:bg-orange-200 focus:ring-orange-500"
                              : "text-red-700 bg-red-100 hover:bg-red-200 focus:ring-red-500"
                        )}
                      >
                        <Trash2 className="w-4 h-4 mr-1" />
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Usage Modal */}
      {showUsageModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                Model Usage: {showUsageModal.name}
              </h3>
              <button
                onClick={() => setShowUsageModal(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            <div className="space-y-3">
              <p className="text-sm text-gray-600">
                This model is currently used by {showUsageModal.usage_count}{" "}
                agent(s):
              </p>
              <div className="space-y-2">
                {showUsageModal.agents.map((agent) => (
                  <div
                    key={agent.id}
                    className="flex items-center justify-between p-2 bg-gray-50 rounded"
                  >
                    <div>
                      <div className="font-medium text-sm">{agent.name}</div>
                      <div className="text-xs text-gray-500">
                        {agent.agent_type}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-4">
                To delete this model, you must first delete or reconfigure these
                agents.
              </p>
            </div>
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowUsageModal(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                Confirm Delete Model
              </h3>
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
            <div className="mb-6">
              <p className="text-sm text-gray-600">
                Are you sure you want to delete the model "{showDeleteConfirm}"?
              </p>
              <p className="text-xs text-gray-500 mt-2">
                This action cannot be undone.
              </p>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteModel(showDeleteConfirm)}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md"
              >
                Delete Model
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
