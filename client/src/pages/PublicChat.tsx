import React, { useState, useEffect, useRef } from "react";
import { Send, Bot, User, Key, AlertCircle } from "lucide-react";
import { cn } from "../utils/cn";
import { MarkdownContent } from "../components/ui/MarkdownContent";

interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
}

export const PublicChat: React.FC = () => {
  const [apiKey, setApiKey] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Check if API key is in URL params
    const urlParams = new URLSearchParams(window.location.search);
    const keyFromUrl = urlParams.get("key");
    if (keyFromUrl) {
      setApiKey(keyFromUrl);
      handleApiKeySubmit(keyFromUrl);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleApiKeySubmit = async (key?: string) => {
    const keyToUse = key || apiKey;
    if (!keyToUse) return;

    setError(null);
    setIsLoading(true);

    try {
      // Test the API key without counting as usage
      const response = await fetch(
        "http://localhost:8000/api/public/test-key",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            api_key: keyToUse,
          }),
        }
      );

      if (response.ok) {
        setIsAuthenticated(true);
        setSessionId(window.crypto.randomUUID());

        // Add welcome message
        setMessages([
          {
            id: "welcome",
            content: "Hello! I'm your AI assistant. How can I help you today?",
            role: "assistant",
            timestamp: new Date(),
          },
        ]);
      } else if (response.status === 401) {
        setError("Invalid API key. Please check and try again.");
      } else {
        setError("Failed to authenticate. Please try again.");
      }
    } catch (err) {
      setError("Failed to connect to the server.");
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      role: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/api/public/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: apiKey,
          message: inputMessage,
          session_id: sessionId,
        }),
      });

      if (response.ok) {
        const data = await response.json();

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: data.response,
          role: "assistant",
          timestamp: new Date(data.timestamp),
        };

        setMessages((prev) => [...prev, assistantMessage]);
        setSessionId(data.session_id);
      } else if (response.status === 429) {
        setError("Rate limit exceeded. Please try again later.");
      } else {
        setError("Failed to get response. Please try again.");
      }
    } catch (err) {
      setError("Failed to send message. Please check your connection.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (isAuthenticated) {
        sendMessage();
      } else {
        handleApiKeySubmit();
      }
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <div className="bg-white rounded-lg shadow-sm border p-8">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Bot className="w-8 h-8 text-blue-600" />
              </div>
              <h1 className="text-2xl font-bold text-gray-900">AI Assistant</h1>
              <p className="text-gray-600 mt-2">
                Enter your API key to start chatting
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  API Key
                </label>
                <div className="relative">
                  <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="input w-full pl-10"
                    placeholder="iai_********************************"
                    disabled={isLoading}
                  />
                </div>
              </div>

              {error && (
                <div className="flex items-start space-x-2 text-red-600 text-sm">
                  <AlertCircle className="w-4 h-4 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <button
                onClick={() => handleApiKeySubmit()}
                disabled={!apiKey || isLoading}
                className="btn btn-primary w-full"
              >
                {isLoading ? "Authenticating..." : "Start Chatting"}
              </button>
            </div>

            <div className="mt-6 text-center text-sm text-gray-500">
              <p>Don't have an API key?</p>
              <p className="mt-1">Contact the administrator to get access.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <Bot className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">
                  AI Assistant
                </h1>
                <p className="text-sm text-gray-500">Powered by InstantAI</p>
              </div>
            </div>
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span>Connected</span>
            </div>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="flex-1 max-w-4xl w-full mx-auto p-4">
        <div
          className="bg-white rounded-lg shadow-sm border h-full flex flex-col"
          style={{ height: "calc(100vh - 120px)" }}
        >
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex items-start space-x-3",
                  message.role === "user" && "flex-row-reverse space-x-reverse"
                )}
              >
                <div
                  className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                    message.role === "assistant" ? "bg-blue-100" : "bg-gray-100"
                  )}
                >
                  {message.role === "assistant" ? (
                    <Bot className="w-4 h-4 text-blue-600" />
                  ) : (
                    <User className="w-4 h-4 text-gray-600" />
                  )}
                </div>
                <div
                  className={cn(
                    "flex-1 rounded-lg px-4 py-2",
                    message.role === "assistant"
                      ? "bg-gray-100 text-gray-900"
                      : "bg-blue-600 text-white"
                  )}
                >
                  {message.role === "assistant" ? (
                    <MarkdownContent content={message.content} />
                  ) : (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  )}
                  <p
                    className={cn(
                      "text-xs mt-1",
                      message.role === "assistant"
                        ? "text-gray-500"
                        : "text-blue-200"
                    )}
                  >
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <Bot className="w-4 h-4 text-blue-600" />
                </div>
                <div className="bg-gray-100 rounded-lg px-4 py-2">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.1s" }}
                    ></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    ></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t p-4">
            {error && (
              <div className="flex items-center space-x-2 text-red-600 text-sm mb-2">
                <AlertCircle className="w-4 h-4" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex items-end space-x-2">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message..."
                className="flex-1 input resize-none"
                rows={1}
                disabled={isLoading}
              />
              <button
                onClick={sendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className="btn btn-primary p-2"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
