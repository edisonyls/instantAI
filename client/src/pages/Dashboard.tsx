import React, { useState, useEffect, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  FileText,
  Key,
  Trash2,
  Copy,
  CheckCircle,
  Plus,
  Brain,
  Eye,
  EyeOff,
} from "lucide-react";
import { cn } from "../utils/cn";
import { deleteKnowledgeBase } from "../services/api";

interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  total_documents: number;
  total_chunks: number;
  created_at: string;
  updated_at: string;
}

interface APIKey {
  key: string;
  knowledge_base_id: string;
  name: string;
  created_at: string;
  last_used?: string;
  usage_count: number;
  is_active: boolean;
}

interface Document {
  id: string;
  filename: string;
  text_length: number;
  chunk_count: number;
  upload_timestamp: string;
}

export const Dashboard: React.FC = () => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [apiKey, setApiKey] = useState<APIKey | null>(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [kbName, setKbName] = useState("");
  const [kbDescription, setKbDescription] = useState("");

  const fetchKnowledgeBases = useCallback(async () => {
    try {
      const response = await fetch("http://localhost:8000/api/knowledge-bases");
      const data = await response.json();
      setKnowledgeBases(data.knowledge_bases || []);

      // Select first KB if available
      if (data.knowledge_bases?.length > 0 && !selectedKb) {
        selectKnowledgeBase(data.knowledge_bases[0]);
      }
    } catch (error) {
      console.error("Error fetching knowledge bases:", error);
    }
  }, [selectedKb]);

  useEffect(() => {
    fetchKnowledgeBases();
  }, [fetchKnowledgeBases]);

  const selectKnowledgeBase = async (kb: KnowledgeBase) => {
    setSelectedKb(kb);
    setLoading(true);

    try {
      const response = await fetch(
        `http://localhost:8000/api/knowledge-bases/${kb.id}`
      );
      const data = await response.json();
      setDocuments(data.documents || []);
      setApiKey(data.api_key);
    } catch (error) {
      console.error("Error fetching knowledge base details:", error);
    } finally {
      setLoading(false);
    }
  };

  const createKnowledgeBase = async () => {
    if (!kbName) return;

    try {
      const response = await fetch(
        "http://localhost:8000/api/knowledge-bases",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: kbName,
            description: kbDescription || undefined,
          }),
        }
      );

      if (response.ok) {
        const data = await response.json();
        await fetchKnowledgeBases();
        selectKnowledgeBase(data.knowledge_base);
        setShowCreateModal(false);
        setKbName("");
        setKbDescription("");
      }
    } catch (error) {
      console.error("Error creating knowledge base:", error);
    }
  };

  const onDrop = async (acceptedFiles: File[]) => {
    if (!selectedKb) return;

    const formData = new FormData();
    acceptedFiles.forEach((file) => {
      formData.append("files", file);
    });

    try {
      const response = await fetch(
        `http://localhost:8000/api/knowledge-bases/${selectedKb.id}/documents`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (response.ok) {
        await selectKnowledgeBase(selectedKb);
      }
    } catch (error) {
      console.error("Error uploading documents:", error);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
    },
    maxSize: 10 * 1024 * 1024,
  });

  const copyApiKey = () => {
    if (apiKey) {
      navigator.clipboard.writeText(apiKey.key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const deleteDocument = async (docId: string) => {
    if (
      !selectedKb ||
      !window.confirm("Are you sure you want to delete this document?")
    )
      return;

    try {
      const response = await fetch(
        `http://localhost:8000/api/knowledge-bases/${selectedKb.id}/documents/${docId}`,
        { method: "DELETE" }
      );

      if (response.ok) {
        await selectKnowledgeBase(selectedKb);
      }
    } catch (error) {
      console.error("Error deleting document:", error);
    }
  };

  const deleteKnowledgeBaseHandler = async (kbId: string, kbName: string) => {
    if (
      !window.confirm(
        `Are you sure you want to delete the knowledge base "${kbName}"? This will permanently delete all documents, API keys, and associated data.`
      )
    )
      return;

    try {
      await deleteKnowledgeBase(kbId);
      
      // If the deleted KB was selected, clear the selection
      if (selectedKb?.id === kbId) {
        setSelectedKb(null);
        setDocuments([]);
        setApiKey(null);
      }
      
      // Refresh the knowledge bases list
      await fetchKnowledgeBases();
    } catch (error) {
      console.error("Error deleting knowledge base:", error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <span className="text-gray-600">Loading...</span>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Knowledge Base Dashboard
        </h1>
        <p className="text-gray-600 mt-1">Manage your AI agents and API keys</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Knowledge Bases List */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm border">
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="text-lg font-semibold">Knowledge Bases</h2>
              <button
                onClick={() => setShowCreateModal(true)}
                className="btn btn-primary btn-sm flex items-center space-x-1"
              >
                <Plus className="w-4 h-4" />
                <span>New</span>
              </button>
            </div>

            <div className="p-4 space-y-2">
              {knowledgeBases.map((kb) => (
                <div
                  key={kb.id}
                  className={cn(
                    "w-full p-3 rounded-lg transition-colors border",
                    selectedKb?.id === kb.id
                      ? "bg-blue-50 border-blue-200"
                      : "bg-white border-gray-200 hover:border-gray-300"
                  )}
                >
                  <div className="flex items-start justify-between">
                    <button
                      onClick={() => selectKnowledgeBase(kb)}
                      className="flex-1 text-left"
                    >
                      <div>
                        <h3 className="font-medium text-gray-900">{kb.name}</h3>
                        {kb.description && (
                          <p className="text-sm text-gray-600 mt-1">
                            {kb.description}
                          </p>
                        )}
                        <div className="flex items-center space-x-3 mt-2 text-xs text-gray-500">
                          <span>{kb.total_documents} docs</span>
                          <span>{kb.total_chunks} chunks</span>
                        </div>
                      </div>
                    </button>
                    <div className="flex items-center space-x-2 ml-3">
                      <Brain className="w-5 h-5 text-gray-400" />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteKnowledgeBaseHandler(kb.id, kb.name);
                        }}
                        className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                        title="Delete knowledge base"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}

              {knowledgeBases.length === 0 && (
                <p className="text-center text-gray-500 py-8">
                  No knowledge bases yet. Create one to get started.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Selected Knowledge Base Details */}
        <div className="lg:col-span-2 space-y-6">
          {selectedKb ? (
            <>
              {/* API Key Section */}
              <div className="bg-white rounded-lg shadow-sm border p-6">
                <h2 className="text-lg font-semibold mb-4 flex items-center">
                  <Key className="w-5 h-5 mr-2" />
                  API Key
                </h2>

                {apiKey && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Your API Key
                      </label>
                      <div className="flex items-center space-x-2">
                        <div className="flex-1 font-mono text-sm bg-gray-50 p-3 rounded-lg border">
                          {showApiKey
                            ? apiKey.key
                            : "iai_********************************"}
                        </div>
                        <button
                          onClick={() => setShowApiKey(!showApiKey)}
                          className="btn btn-outline btn-sm"
                        >
                          {showApiKey ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={copyApiKey}
                          className="btn btn-outline btn-sm flex items-center space-x-1"
                        >
                          {copied ? (
                            <>
                              <CheckCircle className="w-4 h-4 text-green-600" />
                              <span>Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-4 h-4" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">Usage:</span>
                        <span className="ml-2 font-medium">
                          {apiKey.usage_count} requests
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">Status:</span>
                        <span className="ml-2">
                          {apiKey.is_active ? (
                            <span className="text-green-600">Active</span>
                          ) : (
                            <span className="text-red-600">Inactive</span>
                          )}
                        </span>
                      </div>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4">
                      <h4 className="font-medium text-sm mb-2">
                        Integration Example
                      </h4>
                      <pre className="text-xs overflow-x-auto">
                        {`curl -X POST http://localhost:8000/api/public/chat \\
  -H "Content-Type: application/json" \\
  -d '{
    "api_key": "${showApiKey ? apiKey.key : "iai_********************************"}",
    "message": "Your question here"
  }'`}
                      </pre>
                    </div>
                  </div>
                )}
              </div>

              {/* Documents Section */}
              <div className="bg-white rounded-lg shadow-sm border">
                <div className="p-4 border-b">
                  <h2 className="text-lg font-semibold flex items-center">
                    <FileText className="w-5 h-5 mr-2" />
                    Documents ({documents.length})
                  </h2>
                </div>

                <div className="p-6">
                  {/* Upload Area */}
                  <div
                    {...getRootProps()}
                    className={cn(
                      "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
                      isDragActive
                        ? "border-blue-400 bg-blue-50"
                        : "border-gray-300 hover:border-gray-400"
                    )}
                  >
                    <input {...getInputProps()} />
                    <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">
                      {isDragActive
                        ? "Drop the files here..."
                        : "Drag & drop Word documents here, or click to select"}
                    </p>
                    <p className="text-sm text-gray-500 mt-2">
                      Supports multiple .docx files (10MB total)
                    </p>
                  </div>

                  {/* Documents List */}
                  {documents.length > 0 && (
                    <div className="mt-6 space-y-2">
                      {documents.map((doc) => (
                        <div
                          key={doc.id}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                        >
                          <div className="flex items-center space-x-3">
                            <FileText className="w-5 h-5 text-gray-400" />
                            <div>
                              <p className="font-medium text-sm">
                                {doc.filename}
                              </p>
                              <p className="text-xs text-gray-500">
                                {doc.chunk_count} chunks •{" "}
                                {(doc.text_length / 1000).toFixed(1)}k chars
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => deleteDocument(doc.id)}
                            className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-lg shadow-sm border p-12 text-center">
              <Brain className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                Select a Knowledge Base
              </h3>
              <p className="text-gray-600">
                Choose a knowledge base from the list or create a new one to get
                started
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Create Knowledge Base Modal */}
      {showCreateModal && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowCreateModal(false);
            }
          }}
        >
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-xl font-semibold mb-6 text-gray-900">
              Create Knowledge Base
            </h3>

            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Name *
                </label>
                <input
                  type="text"
                  value={kbName}
                  onChange={(e) => setKbName(e.target.value)}
                  className="input w-full"
                  placeholder="My AI Agent"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && kbName.trim()) {
                      createKnowledgeBase();
                    } else if (e.key === 'Escape') {
                      setShowCreateModal(false);
                    }
                  }}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description (optional)
                </label>
                <textarea
                  value={kbDescription}
                  onChange={(e) => setKbDescription(e.target.value)}
                  className="input w-full resize-none"
                  rows={3}
                  placeholder="Describe what this agent will help with..."
                  onKeyDown={(e) => {
                    if (e.key === 'Escape') {
                      setShowCreateModal(false);
                    }
                  }}
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 mt-8">
              <button
                onClick={() => setShowCreateModal(false)}
                className="btn btn-outline px-5 py-2.5 min-w-[90px]"
              >
                Cancel
              </button>
              <button
                onClick={createKnowledgeBase}
                disabled={!kbName.trim()}
                className={`btn btn-primary px-5 py-2.5 min-w-[90px] transition-all duration-200 ${
                  !kbName.trim() ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-lg'
                }`}
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
