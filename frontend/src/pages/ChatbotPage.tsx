import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Send, Bot, User, Lightbulb, Building, Target, Sparkles, ArrowRight, Plus } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { ConfirmDialog } from "../components/ui/confirm-dialog";
import { IncentiveModal } from "../components/IncentiveModal";
import { CompanyModal } from "../components/CompanyModal";
import { apiClient } from "../api/client";
import type { ChatMessage } from "../types";

// Helper function to translate tool names to Portuguese
const getToolDisplayName = (toolName: string): string => {
  const toolNames: Record<string, string> = {
    "semantic_search": "Busca semântica",
    "get_incentive_by_id": "Consultar incentivo",
    "get_company_by_name": "Consultar empresa",
    "search_incentives_by_title": "Procurar incentivos",
    "search_companies_by_sector": "Procurar empresas por setor",
    "search_companies_semantic": "Busca semântica de empresas",
    "get_matches_for_company": "Obter correspondências para empresa",
    "get_matches_for_incentive": "Obter correspondências para incentivo",
    "get_matches_for_incentive_by_title": "Obter correspondências por título",
    "get_statistics": "Obter estatísticas"
  };
  return toolNames[toolName] || toolName;
};

export function ChatbotPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showClearDialog, setShowClearDialog] = useState(false);
  const [currentTools, setCurrentTools] = useState<string[]>([]);
  const [selectedIncentiveId, setSelectedIncentiveId] = useState<number | null>(null);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleNewChat = () => {
    if (isLoading) return;

    // Show confirmation dialog if there are messages
    if (messages.length > 0) {
      setShowClearDialog(true);
    } else {
      clearConversation();
    }
  };

  const clearConversation = () => {
    setMessages([]);
    setInput("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setCurrentTools([]); // Reset tools for new query

    try {
      const stream = await apiClient.sendMessage(input, messages);
      const reader = stream.getReader();
      const decoder = new TextDecoder();

      let assistantMessage = "";
      let messageMetadata: any = null;
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") continue;

            // Check for tool call events
            if (data.startsWith("__TOOL_CALL__:")) {
              try {
                const toolJson = data.slice(14); // Remove "__TOOL_CALL__:" prefix
                const toolData = JSON.parse(toolJson);
                console.log("🔧 Tool call received:", toolData.tool_name);

                // Add tool to currentTools array
                setCurrentTools((prev) => [...prev, toolData.tool_name]);
              } catch (e) {
                console.error("Error parsing tool call:", e);
              }
            }
            // Check for tool result events
            else if (data.startsWith("__TOOL_RESULT__:")) {
              try {
                const toolJson = data.slice(16); // Remove "__TOOL_RESULT__:" prefix
                const toolData = JSON.parse(toolJson);
                console.log("✅ Tool result received:", toolData.tool_name);
              } catch (e) {
                console.error("Error parsing tool result:", e);
              }
            }
            // Check if this is metadata
            else if (data.startsWith("__METADATA__:")) {
              try {
                const metadataJson = data.slice(13); // Remove "__METADATA__:" prefix
                const metadata = JSON.parse(metadataJson);
                messageMetadata = metadata;

                // Update the last message with metadata
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = {
                    ...newMessages[newMessages.length - 1],
                    metadata,
                  };
                  return newMessages;
                });
                // Keep currentTools for final display
                if (metadata.tools_used) {
                  setCurrentTools(metadata.tools_used);
                }
              } catch (e) {
                console.error("Error parsing metadata:", e);
              }
            } else {
              // Regular text chunk - JSON decode to handle newlines
              try {
                const textContent = JSON.parse(data);
                assistantMessage += textContent;
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = {
                    ...assistantMsg,
                    content: assistantMessage,
                    metadata: messageMetadata, // Preserve metadata
                  };
                  return newMessages;
                });
              } catch (e) {
                // Fallback: treat as plain text if not valid JSON
                assistantMessage += data;
                setMessages((prev) => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = {
                    ...assistantMsg,
                    content: assistantMessage,
                    metadata: messageMetadata, // Preserve metadata
                  };
                  return newMessages;
                });
              }
            }
          }
        }
      }
    } catch (error) {
      console.error("Error sending message:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Desculpe, ocorreu um erro ao processar sua mensagem.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Messages Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-slate-500 max-w-lg">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-slate-800 to-slate-600 mx-auto mb-6 flex items-center justify-center shadow-lg">
                  <Bot className="w-10 h-10 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-slate-800 mb-3">
                  Como posso ajudar?
                </h2>
                <p className="text-slate-600 mb-8 leading-relaxed">
                  Faça perguntas sobre incentivos públicos, empresas ou correspondências
                </p>
                <div className="bg-slate-50 rounded-xl p-6 text-left">
                  <p className="text-sm font-semibold text-slate-800 mb-4 flex items-center gap-2">
                    <span className="w-2 h-2 bg-slate-600 rounded-full"></span>
                    Exemplos de perguntas:
                  </p>
                  <div className="space-y-3">
                    <button
                      onClick={() => setInput("Quais incentivos estão disponíveis para tecnologia?")}
                      className="flex items-start gap-3 p-3 bg-white rounded-lg border border-slate-200 hover:border-slate-300 transition-colors cursor-pointer w-full text-left"
                    >
                      <Lightbulb className="w-5 h-5 text-slate-400 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-slate-700">"Quais incentivos estão disponíveis para tecnologia?"</p>
                    </button>
                    <button
                      onClick={() => setInput("Mostra-me empresas do setor de energia renovável")}
                      className="flex items-start gap-3 p-3 bg-white rounded-lg border border-slate-200 hover:border-slate-300 transition-colors cursor-pointer w-full text-left"
                    >
                      <Building className="w-5 h-5 text-slate-400 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-slate-700">"Mostra-me empresas do setor de energia renovável"</p>
                    </button>
                    <button
                      onClick={() => setInput("Quais são as melhores empresas para o incentivo Apoio a Infraestruturas de Base Tecnológica?")}
                      className="flex items-start gap-3 p-3 bg-white rounded-lg border border-slate-200 hover:border-slate-300 transition-colors cursor-pointer w-full text-left"
                    >
                      <Target className="w-5 h-5 text-slate-400 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-slate-700">"Quais são as melhores empresas para o incentivo X?"</p>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

        {messages.map((message, index) => {
          // 🔍 DEBUG: Log message for debugging
          if (message.role === "assistant" && message.metadata) {
            console.log(`Message ${index}:`, {
              hasContent: !!message.content,
              contentLength: message.content?.length,
              hasMetadata: !!message.metadata,
              hasSuggestedActions: !!message.metadata?.suggested_actions,
              suggestedActionsCount: message.metadata?.suggested_actions?.length
            });
          }

          return (
          <div
            key={index}
            className={`flex gap-4 ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {message.role === "assistant" && (
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-800 to-slate-600 flex items-center justify-center flex-shrink-0 shadow-md">
                <Bot className="w-5 h-5 text-white" />
              </div>
            )}
            <div className="max-w-[75%] flex flex-col gap-3">
              <div
                className={`rounded-xl p-4 shadow-sm ${
                  message.role === "user"
                    ? "bg-slate-900 text-white"
                    : "bg-slate-50 border border-slate-200"
                }`}
              >
                {message.role === "assistant" ? (
                  <div className="prose prose-slate prose-sm max-w-none prose-headings:font-bold prose-headings:text-slate-900 prose-h1:text-xl prose-h1:mt-6 prose-h1:mb-3 prose-h1:border-b prose-h1:border-slate-200 prose-h1:pb-2 prose-h2:text-lg prose-h2:mt-5 prose-h2:mb-2 prose-h3:text-base prose-h3:mt-4 prose-h3:mb-2 prose-p:my-3 prose-p:text-slate-700 prose-p:leading-relaxed prose-ul:my-3 prose-ul:space-y-1 prose-ol:my-3 prose-ol:space-y-1 prose-li:text-slate-700 prose-code:text-xs prose-code:bg-slate-200 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:font-mono prose-code:text-slate-800 prose-pre:bg-slate-900 prose-pre:text-slate-100 prose-pre:p-4 prose-pre:rounded-lg prose-strong:font-bold prose-strong:text-slate-900 prose-a:text-blue-600 prose-a:underline prose-a:cursor-pointer hover:prose-a:text-blue-800 prose-hr:my-6 prose-hr:border-slate-300">
                    {message.content ? (
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    ) : (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2 text-slate-600">
                          <div className="flex gap-1">
                            <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                            <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                            <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                          </div>
                          <span className="text-sm font-medium">Pensando</span>
                        </div>
                        {currentTools.length > 0 && (() => {
                          // Aggregate duplicate tool names with counts
                          const toolCounts = currentTools.reduce((acc, tool) => {
                            acc[tool] = (acc[tool] || 0) + 1;
                            return acc;
                          }, {} as Record<string, number>);

                          return (
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(toolCounts).map(([tool, count]) => (
                                <div
                                  key={tool}
                                  className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 text-slate-700 rounded-md text-xs font-medium border border-slate-200"
                                >
                                  <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>
                                  <span>{getToolDisplayName(tool)}</span>
                                  {count > 1 && (
                                    <span className="ml-0.5 px-1.5 py-0.5 bg-slate-200 text-slate-600 rounded text-xs font-semibold">
                                      {count}×
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          );
                        })()}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">
                    {message.content}
                  </p>
                )}
              </div>

              {/* Metadata - Suggested Actions */}
              {message.role === "assistant" && message.metadata?.suggested_actions && message.metadata.suggested_actions.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {message.metadata.suggested_actions.map((action, idx) => (
                    <button
                      key={idx}
                      className="inline-flex items-center gap-2 px-4 py-2.5 text-sm bg-slate-900 text-white border border-slate-900 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50 font-medium"
                      disabled={isLoading}
                      onClick={async () => {
                        if (isLoading) return;

                        // Handle different action types
                        if (action.action_type === "view_incentive") {
                          // Open modal with incentive details
                          const incentiveId = action.action_data?.id;
                          if (incentiveId) {
                            setSelectedIncentiveId(incentiveId);
                          } else {
                            // Fallback: navigate to incentives page
                            const incentiveTitle = action.action_data?.title;
                            if (incentiveTitle) {
                              navigate(`/incentives?search=${encodeURIComponent(incentiveTitle)}`);
                            } else {
                              navigate("/incentives");
                            }
                          }
                        } else if (action.action_type === "view_company") {
                          // Open modal with company details
                          const companyId = action.action_data?.id;
                          if (companyId) {
                            setSelectedCompanyId(companyId);
                          } else {
                            // Fallback: navigate to companies page
                            const companyName = action.action_data?.name;
                            if (companyName) {
                              navigate(`/companies?search=${encodeURIComponent(companyName)}`);
                            } else {
                              navigate("/companies");
                            }
                          }
                        } else if (action.action_type === "question" && action.action_data?.query) {
                          // Auto-send the suggested question
                          const query = action.action_data.query;
                          const userMessage: ChatMessage = {
                            role: "user",
                            content: query,
                            timestamp: new Date().toISOString(),
                          };

                          setMessages((prev) => [...prev, userMessage]);
                          setIsLoading(true);
                          setCurrentTools([]); // Reset tools for new query

                          try {
                            const stream = await apiClient.sendMessage(query, messages);
                            const reader = stream.getReader();
                            const decoder = new TextDecoder();

                            let assistantMessage = "";
                            let messageMetadata: any = null;
                            const assistantMsg: ChatMessage = {
                              role: "assistant",
                              content: "",
                              timestamp: new Date().toISOString(),
                            };

                            setMessages((prev) => [...prev, assistantMsg]);

                            while (true) {
                              const { done, value } = await reader.read();
                              if (done) break;

                              const chunk = decoder.decode(value);
                              const lines = chunk.split("\n\n");

                              for (const line of lines) {
                                if (line.startsWith("data: ")) {
                                  const data = line.slice(6);
                                  if (data === "[DONE]") continue;

                                  // Check for tool call events
                                  if (data.startsWith("__TOOL_CALL__:")) {
                                    try {
                                      const toolJson = data.slice(14);
                                      const toolData = JSON.parse(toolJson);
                                      setCurrentTools((prev) => [...prev, toolData.tool_name]);
                                    } catch (e) {
                                      console.error("Error parsing tool call:", e);
                                    }
                                  }
                                  // Check for tool result events
                                  else if (data.startsWith("__TOOL_RESULT__:")) {
                                    // Tool completed - could add visual feedback here
                                  }
                                  // Check if this is metadata
                                  else if (data.startsWith("__METADATA__:")) {
                                    try {
                                      const metadataJson = data.slice(13);
                                      const metadata = JSON.parse(metadataJson);
                                      messageMetadata = metadata;
                                      setMessages((prev) => {
                                        const newMessages = [...prev];
                                        newMessages[newMessages.length - 1] = {
                                          ...newMessages[newMessages.length - 1],
                                          metadata,
                                        };
                                        return newMessages;
                                      });
                                      // Update currentTools for display during thinking phase
                                      if (metadata.tools_used) {
                                        setCurrentTools(metadata.tools_used);
                                      }
                                    } catch (e) {
                                      console.error("Error parsing metadata:", e);
                                    }
                                  } else {
                                    // Regular text chunk - JSON decode to handle newlines
                                    try {
                                      const textContent = JSON.parse(data);
                                      assistantMessage += textContent;
                                    } catch (e) {
                                      // Fallback: treat as plain text
                                      assistantMessage += data;
                                    }
                                    setMessages((prev) => {
                                      const newMessages = [...prev];
                                      newMessages[newMessages.length - 1] = {
                                        ...assistantMsg,
                                        content: assistantMessage,
                                        metadata: messageMetadata, // Preserve metadata
                                      };
                                      return newMessages;
                                    });
                                  }
                                }
                              }
                            }
                          } catch (error) {
                            console.error("Error sending suggested action:", error);
                            setMessages((prev) => [
                              ...prev,
                              {
                                role: "assistant",
                                content: "Desculpe, ocorreu um erro ao processar sua mensagem.",
                                timestamp: new Date().toISOString(),
                              },
                            ]);
                          } finally {
                            setIsLoading(false);
                          }
                        }
                      }}
                    >
                      <ArrowRight className="w-3 h-3 text-white" />
                      <span className="text-white">{action.label}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Metadata - Sources/Tools indicator */}
              {message.role === "assistant" && message.metadata?.tools_used && message.metadata.tools_used.length > 0 && (() => {
                // Aggregate duplicate tool names with counts
                const toolCounts = message.metadata.tools_used.reduce((acc, tool) => {
                  acc[tool] = (acc[tool] || 0) + 1;
                  return acc;
                }, {} as Record<string, number>);

                return (
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <Sparkles className="w-3 h-3" />
                    <span>Ferramentas usadas:</span>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(toolCounts).map(([tool, count]) => (
                        <span key={tool} className="bg-slate-100 px-2 py-0.5 rounded">
                          {getToolDisplayName(tool)}
                          {count > 1 && <span className="ml-1 font-semibold text-slate-600">{count}×</span>}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })()}
            </div>
            {message.role === "user" && (
              <div className="w-10 h-10 rounded-xl bg-slate-200 flex items-center justify-center flex-shrink-0 shadow-sm">
                <User className="w-5 h-5 text-slate-700" />
              </div>
            )}
          </div>
          );
        })}
        {isLoading && messages[messages.length - 1]?.role === "user" && (
          <div className="flex gap-4 justify-start">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-800 to-slate-600 flex items-center justify-center flex-shrink-0 shadow-md">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-slate-50 border border-slate-200 shadow-sm rounded-xl p-4">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-slate-200 p-6 bg-white">
          <div className="max-w-4xl mx-auto space-y-3">
            <form onSubmit={handleSubmit} className="flex gap-3">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Digite sua mensagem..."
                disabled={isLoading}
                className="flex-1 h-14 px-5 border-slate-300 rounded-2xl bg-slate-50 focus:bg-white focus:ring-2 focus:ring-slate-500 focus:border-transparent transition-all"
                autoFocus
              />
              <Button
                type="button"
                onClick={handleNewChat}
                disabled={isLoading || messages.length === 0}
                className="h-14 px-4 bg-slate-100 text-slate-700 rounded-2xl font-medium transition-all duration-200 hover:bg-slate-200 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                size="default"
                title="Nova conversa"
              >
                <Plus className="w-5 h-5" />
                <span className="hidden sm:inline text-sm">Nova</span>
              </Button>
              <Button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="h-14 w-14 bg-slate-900 text-white rounded-2xl font-medium transition-all duration-200 hover:bg-slate-800 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                size="default"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </Button>
            </form>
          </div>
          <p className="text-xs text-slate-500 mt-3 text-center max-w-4xl mx-auto">
            As respostas são geradas por IA e podem conter erros
          </p>
        </div>
      </div>

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showClearDialog}
        onClose={() => setShowClearDialog(false)}
        onConfirm={clearConversation}
        title="Nova Conversa"
        description="Tem certeza que deseja iniciar uma nova conversa? A conversa atual será perdida e não poderá ser recuperada."
        confirmText="Sim, começar nova"
        cancelText="Cancelar"
        variant="warning"
      />

      {/* Incentive Modal */}
      {selectedIncentiveId && (
        <IncentiveModal
          incentiveId={selectedIncentiveId}
          isOpen={selectedIncentiveId !== null}
          onClose={() => setSelectedIncentiveId(null)}
        />
      )}

      {/* Company Modal */}
      {selectedCompanyId && (
        <CompanyModal
          companyId={selectedCompanyId}
          isOpen={selectedCompanyId !== null}
          onClose={() => setSelectedCompanyId(null)}
        />
      )}
    </div>
  );
}
