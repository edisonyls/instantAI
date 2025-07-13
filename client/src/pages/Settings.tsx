import React, { useState, useEffect } from "react";
import {
  Settings as SettingsIcon,
  Server,
  Database,
  Brain,
  RefreshCw,
} from "lucide-react";
import { getHealthStatus, HealthStatus, getSystemInfo, SystemInfo } from "../services/api";

export const Settings: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [infoLoading, setInfoLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [infoError, setInfoError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

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
            refreshing ? 'opacity-75 cursor-not-allowed' : ''
          }`}
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          <span>{refreshing ? 'Refreshing...' : 'Refresh All'}</span>
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
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {typeof status === "string" ? status : status.status}
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
                  {systemInfo.ai_configuration.max_context_length.toLocaleString()} characters
                </p>
              </div>
              
              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Similarity Threshold
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.ai_configuration.similarity_threshold}
                </p>
              </div>
              
              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Retrieved Chunks
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.ai_configuration.max_retrieved_chunks}
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
                  {systemInfo.document_processing.chunk_size.toLocaleString()} characters
                </p>
              </div>
              
              <div className="bg-gray-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Chunk Overlap
                </label>
                <p className="text-gray-900 font-mono text-sm">
                  {systemInfo.document_processing.chunk_overlap.toLocaleString()} characters
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
            <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">
              System Configuration
            </h3>
            <p className="mt-1 text-sm text-blue-700">
              This information is currently read-only and reflects the backend configuration. 
              To modify these values, update the configuration file or environment variables and restart the backend service.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
