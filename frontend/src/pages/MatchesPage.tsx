import { useState, useEffect } from "react";
import { TrendingUp, Building2, Loader2, FolderOpen, AlertCircle, Award, Trophy, Play, RefreshCw, ChevronLeft, ChevronRight, Download } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/card";
import { CompanyModal } from "../components/CompanyModal";
import { IncentiveModal } from "../components/IncentiveModal";
import { apiClient } from "../api/client";
import type { Match, Incentive } from "../types";

export function MatchesPage() {
  const [incentives, setIncentives] = useState<Incentive[]>([]);
  const [matchesByIncentive, setMatchesByIncentive] = useState<Record<number, Match[]>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const [totalIncentives, setTotalIncentives] = useState(0);
  const incentivesPerPage = 50;
  
  // Modal states
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [selectedIncentiveId, setSelectedIncentiveId] = useState<number | null>(null);
  const [isCompanyModalOpen, setIsCompanyModalOpen] = useState(false);
  const [isIncentiveModalOpen, setIsIncentiveModalOpen] = useState(false);
  
  // Matching states
  const [isGeneratingMatches, setIsGeneratingMatches] = useState(false);
  const [matchingResults, setMatchingResults] = useState<string | null>(null);
  const [runningIncentiveId, setRunningIncentiveId] = useState<number | null>(null);
  const [isExporting, setIsExporting] = useState(false);

  // Progress tracking states
  const [progressCurrent, setProgressCurrent] = useState(0);
  const [progressTotal, setProgressTotal] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [progressLogs, setProgressLogs] = useState<string[]>([]);

  useEffect(() => {
    loadData();
  }, [currentPage]); // Also reload when page changes

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Get total count for accurate pagination (only on first load)
      if (currentPage === 1) {
        const countResponse = await apiClient.countIncentives();
        setTotalIncentives(countResponse.count);
      }
      
      // Calculate pagination parameters
      const skip = (currentPage - 1) * incentivesPerPage;
      
      // Load incentives for current page
      const incentivesData = await apiClient.getIncentives({ 
        limit: incentivesPerPage,
        skip: skip
      });
      setIncentives(incentivesData);

      // Load top matches for each incentive on current page
      const matchesData: Record<number, Match[]> = {};
      for (const incentive of incentivesData) {
        try {
          const matches = await apiClient.getTopMatchesForIncentive(incentive.id);
          matchesData[incentive.id] = matches;
        } catch (err) {
          console.error(`Error loading matches for incentive ${incentive.id}:`, err);
          matchesData[incentive.id] = [];
        }
      }
      setMatchesByIncentive(matchesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar dados");
    } finally {
      setIsLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 4) return "text-green-600";
    if (score >= 3) return "text-yellow-600";
    return "text-red-600";
  };

  const formatScore = (score: number) => {
    return score.toFixed(2);
  };

  const handleCompanyClick = (companyId: number) => {
    setSelectedCompanyId(companyId);
    setIsCompanyModalOpen(true);
  };

  const handleIncentiveClick = (incentiveId: number) => {
    setSelectedIncentiveId(incentiveId);
    setIsIncentiveModalOpen(true);
  };

  const closeCompanyModal = () => {
    setIsCompanyModalOpen(false);
    setSelectedCompanyId(null);
  };

  const closeIncentiveModal = () => {
    setIsIncentiveModalOpen(false);
    setSelectedIncentiveId(null);
  };

  const handleGenerateMatches = async (forceRefresh: boolean = false) => {
    setIsGeneratingMatches(true);
    setMatchingResults(null);
    setProgressCurrent(0);
    setProgressTotal(0);
    setProgressMessage("");
    setProgressLogs([]);

    try {
      await apiClient.runBatchMatchingStream(
        { force_refresh: forceRefresh },
        (data) => {
          // Handle different event types
          switch (data.type) {
            case "start":
              setProgressTotal(data.total);
              setProgressMessage(data.message);
              setProgressLogs(prev => [...prev, `🚀 ${data.message}`]);
              break;

            case "progress":
              setProgressCurrent(data.current);
              setProgressMessage(data.message);
              break;

            case "success":
              setProgressCurrent(data.current);
              setProgressLogs(prev => [...prev, data.message]);
              break;

            case "error":
              setProgressLogs(prev => [...prev, `❌ ${data.message}`]);
              break;

            case "complete":
              setProgressCurrent(data.total_incentives);
              const message = `✅ Completed: ${data.successful_matches} successful, ${data.failed_matches} failed`;
              setMatchingResults(message);
              setProgressLogs(prev => [...prev, message]);
              break;

            case "warning":
              setProgressLogs(prev => [...prev, `⚠️ ${data.message}`]);
              break;

            case "info":
              setProgressLogs(prev => [...prev, `ℹ️ ${data.message}`]);
              break;
          }
        }
      );

      // Reload the data to show new matches
      await loadData();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to generate matches";
      setMatchingResults(`Error: ${errorMessage}`);
      setProgressLogs(prev => [...prev, `❌ Error: ${errorMessage}`]);
    } finally {
      setIsGeneratingMatches(false);
    }
  };

  const handleRunMatchingForIncentive = async (incentiveId: number) => {
    setRunningIncentiveId(incentiveId);

    try {
      const result = await apiClient.runMatchingForIncentive({
        incentive_id: incentiveId
      });

      // Reload matches from database to get complete data
      try {
        const matches = await apiClient.getTopMatchesForIncentive(incentiveId);
        setMatchesByIncentive(prev => ({
          ...prev,
          [incentiveId]: matches
        }));
      } catch (err) {
        console.error(`Error loading matches for incentive ${incentiveId}:`, err);
        // Fallback: use the result data if reload fails
        setMatchesByIncentive(prev => ({
          ...prev,
          [incentiveId]: result.matches.map((match) => ({
            id: match.company_id,
            incentive_id: incentiveId,
            company_id: match.company_id,
            score: match.score,
            rank_position: match.rank,
            reasoning: match.reasoning,
            created_at: new Date().toISOString(),
            company: {
              id: match.company_id,
              company_name: match.company_name
            }
          }))
        }));
      }

      // Show success message briefly
      const message = `✅ Match gerado com sucesso! ${result.matches.length} empresas encontradas em ${result.processing_time.toFixed(2)}s`;
      setMatchingResults(message);
      setTimeout(() => setMatchingResults(null), 5000);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to run matching";
      setMatchingResults(`❌ Error: ${errorMessage}`);
      setTimeout(() => setMatchingResults(null), 5000);
    } finally {
      setRunningIncentiveId(null);
    }
  };

  const handleExportMatches = async () => {
    setIsExporting(true);
    try {
      const blob = await apiClient.exportMatchesToCSV();

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `incentive_matches_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      // Show success message
      setMatchingResults('✅ CSV exportado com sucesso!');
      setTimeout(() => setMatchingResults(null), 3000);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to export CSV";
      setMatchingResults(`Error: ${errorMessage}`);
      setTimeout(() => setMatchingResults(null), 5000);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-gradient-to-br from-emerald-600 to-teal-600 rounded-xl">
            <TrendingUp className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-slate-800">Correspondências</h1>
            <p className="text-slate-600 mt-1">
              Top 5 empresas mais adequadas para cada incentivo
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleExportMatches}
              disabled={isExporting || isGeneratingMatches}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg font-medium transition-colors duration-200"
              title="Exportar todas as correspondências para CSV"
            >
              {isExporting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Exportando...</span>
                </>
              ) : (
                <>
                  <Download className="w-5 h-5" />
                  <span>Exportar CSV</span>
                </>
              )}
            </button>
            <button
              onClick={() => handleGenerateMatches(false)}
              disabled={isGeneratingMatches}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white rounded-lg font-medium transition-colors duration-200"
            >
              {isGeneratingMatches ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Processando...</span>
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  <span>Processar Matches</span>
                </>
              )}
            </button>
            <button
              onClick={() => handleGenerateMatches(true)}
              disabled={isGeneratingMatches}
              className="flex items-center gap-2 px-4 py-2 bg-slate-600 hover:bg-slate-700 disabled:bg-slate-400 text-white rounded-lg font-medium transition-colors duration-200"
            >
              {isGeneratingMatches ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Regenerando...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-5 h-5" />
                  <span>Regenerar Tudo</span>
                </>
              )}
            </button>
          </div>
        </div>
        
        {/* Progress Bar */}
        {isGeneratingMatches && progressTotal > 0 && (
          <div className="mt-4 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600 font-medium">{progressMessage}</span>
              <span className="text-slate-500">{progressCurrent} / {progressTotal}</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-gradient-to-r from-emerald-500 to-teal-500 h-2.5 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${(progressCurrent / progressTotal) * 100}%` }}
              ></div>
            </div>

            {/* Progress Logs */}
            {progressLogs.length > 0 && (
              <div className="mt-3 max-h-40 overflow-y-auto bg-slate-50 rounded-lg p-3 border border-slate-200">
                <div className="space-y-1 text-xs font-mono">
                  {progressLogs.slice(-10).map((log, index) => (
                    <div key={index} className="text-slate-600">{log}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Matching Results Message */}
        {matchingResults && !isGeneratingMatches && (
          <div className={`mt-4 p-3 rounded-lg ${
            matchingResults.startsWith('Error')
              ? 'bg-red-50 text-red-700 border border-red-200'
              : 'bg-green-50 text-green-700 border border-green-200'
          }`}>
            {matchingResults}
          </div>
        )}
      </div>

      {/* Content Area */}
      <div className="space-y-6">
        {/* Pagination Controls - Top */}
        {totalIncentives > incentivesPerPage && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center justify-between">
              <div className="text-sm text-slate-600">
                Página {currentPage} de {Math.ceil(totalIncentives / incentivesPerPage)} 
                <span className="ml-2">
                  ({((currentPage - 1) * incentivesPerPage) + 1}-{Math.min(currentPage * incentivesPerPage, totalIncentives)} de {totalIncentives} incentivos)
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Anterior
                </button>

                <div className="flex gap-1">
                  {(() => {
                    const totalPages = Math.ceil(totalIncentives / incentivesPerPage);
                    const maxVisiblePages = 5;
                    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
                    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
                    
                    if (endPage - startPage + 1 < maxVisiblePages) {
                      startPage = Math.max(1, endPage - maxVisiblePages + 1);
                    }

                    const pages = [];
                    for (let i = startPage; i <= endPage; i++) {
                      pages.push(i);
                    }

                    return pages.map((page) => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                          currentPage === page
                            ? "bg-slate-900 text-white"
                            : "text-slate-700 bg-white border border-slate-300 hover:bg-slate-50"
                        }`}
                      >
                        {page}
                      </button>
                    ));
                  })()}
                </div>

                <button
                  onClick={() => setCurrentPage(Math.min(Math.ceil(totalIncentives / incentivesPerPage), currentPage + 1))}
                  disabled={currentPage >= Math.ceil(totalIncentives / incentivesPerPage)}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Próxima
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="text-center py-12">
              <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
              <p className="text-red-600 font-medium">{error}</p>
            </div>
          </div>
        )}

        {isLoading && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="text-center py-12">
              <div className="inline-flex items-center gap-3">
                <Loader2 className="w-6 h-6 text-slate-600 animate-spin" />
                <span className="text-slate-600 font-medium">A carregar correspondências...</span>
              </div>
            </div>
          </div>
        )}

        {!isLoading && !error && incentives.length === 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="text-center py-12">
              <FolderOpen className="w-12 h-12 text-slate-400 mx-auto mb-3" />
              <p className="text-slate-600 font-medium">Nenhuma correspondência encontrada</p>
              <p className="text-slate-500 text-sm mt-1">Aguarde o processamento dos matches</p>
            </div>
          </div>
        )}

        {incentives.map((incentive) => {
          const matches = matchesByIncentive[incentive.id] || [];

          return (
            <Card key={incentive.id} className="border-slate-200 hover:shadow-lg transition-shadow duration-200">
              <CardHeader className="bg-gradient-to-r from-slate-50 to-white border-b border-slate-100">
                <div className="flex items-start gap-3">
                  <Award className="w-5 h-5 text-amber-600 flex-shrink-0 mt-1" />
                  <div className="flex-1">
                    <CardTitle
                      className="text-lg leading-tight text-slate-800 cursor-pointer hover:text-amber-600 transition-colors duration-200"
                      onClick={() => handleIncentiveClick(incentive.id)}
                    >
                      {incentive.title}
                    </CardTitle>
                    {incentive.ai_description_structured?.objective && (
                      <CardDescription className="line-clamp-2 mt-2 text-slate-600">
                        {incentive.ai_description_structured.objective}
                      </CardDescription>
                    )}
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRunMatchingForIncentive(incentive.id);
                    }}
                    disabled={runningIncentiveId === incentive.id || isGeneratingMatches}
                    className="flex items-center gap-2 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white text-sm rounded-lg font-medium transition-colors duration-200 flex-shrink-0"
                    title="Gerar ou regenerar correspondências para este incentivo"
                  >
                    {runningIncentiveId === incentive.id ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>A processar...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4" />
                        <span>Processar Match</span>
                      </>
                    )}
                  </button>
                </div>
              </CardHeader>
              <CardContent className="pt-6">
                {matches.length === 0 ? (
                  <div className="text-center py-8">
                    <FolderOpen className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                    <p className="text-sm text-slate-500">
                      Nenhuma correspondência encontrada para este incentivo
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {matches.map((match, index) => (
                      <div
                        key={match.id}
                        className="flex items-start gap-4 p-4 rounded-xl border-2 border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 transition-all duration-200 group"
                      >
                        {/* Rank Badge */}
                        <div className="flex-shrink-0">
                          {index === 0 ? (
                            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-yellow-600 text-white shadow-lg">
                              <Trophy className="w-5 h-5" />
                            </div>
                          ) : (
                            <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-slate-800 text-white font-bold shadow-md">
                              {index + 1}
                            </div>
                          )}
                        </div>

                        {/* Company Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <Building2 className="w-4 h-4 text-slate-400 flex-shrink-0" />
                            <span 
                              className="font-semibold text-slate-800 truncate cursor-pointer hover:text-slate-600 transition-colors duration-200"
                              onClick={() => handleCompanyClick(match.company_id)}
                            >
                              {match.company?.company_name || `Company ${match.company_id}`}
                            </span>
                          </div>
                          {match.company?.cae_primary_label && (
                            <p className="text-sm text-slate-600 line-clamp-1">
                              {match.company.cae_primary_label}
                            </p>
                          )}
                        </div>

                        {/* Scores */}
                        <div className="flex items-center gap-6 flex-shrink-0">
                          {/* Breakdown Scores */}
                          {match.reasoning && (
                            <div className="hidden lg:flex gap-4 text-xs">
                              {match.reasoning.strategic_fit !== undefined && (
                                <div className="text-center px-3 py-2 bg-blue-50 rounded-lg border border-blue-200">
                                  <div className="font-bold text-blue-700 text-sm">
                                    {formatScore(match.reasoning.strategic_fit)}
                                  </div>
                                  <div className="text-blue-600 font-medium">Adequação</div>
                                </div>
                              )}
                              {match.reasoning.quality !== undefined && (
                                <div className="text-center px-3 py-2 bg-purple-50 rounded-lg border border-purple-200">
                                  <div className="font-bold text-purple-700 text-sm">
                                    {formatScore(match.reasoning.quality)}
                                  </div>
                                  <div className="text-purple-600 font-medium">Qualidade</div>
                                </div>
                              )}
                              {match.reasoning.execution_capacity !== undefined && (
                                <div className="text-center px-3 py-2 bg-green-50 rounded-lg border border-green-200">
                                  <div className="font-bold text-green-700 text-sm">
                                    {formatScore(match.reasoning.execution_capacity)}
                                  </div>
                                  <div className="text-green-600 font-medium">Execução</div>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Overall Score */}
                          <div className="text-center px-4 py-2 bg-gradient-to-br from-slate-100 to-slate-50 rounded-xl border-2 border-slate-200 shadow-sm">
                            <div className="flex items-center gap-1.5 mb-1">
                              <TrendingUp className={`w-5 h-5 ${getScoreColor(match.score)}`} />
                              <span className={`font-bold text-xl ${getScoreColor(match.score)}`}>
                                {formatScore(match.score)}
                              </span>
                            </div>
                            <p className="text-xs text-slate-600 font-medium">Score Final</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Modals */}
      {selectedCompanyId && (
        <CompanyModal
          companyId={selectedCompanyId}
          isOpen={isCompanyModalOpen}
          onClose={closeCompanyModal}
        />
      )}
      
      {selectedIncentiveId && (
        <IncentiveModal
          incentiveId={selectedIncentiveId}
          isOpen={isIncentiveModalOpen}
          onClose={closeIncentiveModal}
        />
      )}
    </div>
  );
}
