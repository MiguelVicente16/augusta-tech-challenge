import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, Calendar, DollarSign, ExternalLink, Award, Loader2, FolderOpen, AlertCircle } from "lucide-react";
import { Input } from "../components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/card";
import { IncentiveModal } from "../components/IncentiveModal";
import { apiClient } from "../api/client";
import type { Incentive } from "../types";

export function IncentivesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [incentives, setIncentives] = useState<Incentive[]>([]);
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [selectedIncentiveId, setSelectedIncentiveId] = useState<number | null>(null);
  const [isIncentiveModalOpen, setIsIncentiveModalOpen] = useState(false);

  const ITEMS_PER_PAGE = 10;

  // Update search from URL params on mount
  useEffect(() => {
    const urlSearch = searchParams.get("search");
    const urlId = searchParams.get("id");

    if (urlSearch) {
      setSearch(urlSearch);
    } else if (urlId) {
      // If ID is provided, load that specific incentive
      setSearch(urlId);
    }
  }, [searchParams]);

  useEffect(() => {
    loadIncentives();
  }, [search]);

  const loadIncentives = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.getIncentives({
        search: search || undefined,
        limit: 50,
      });
      setIncentives(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar incentivos");
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("pt-PT");
  };

  const formatBudget = (budget?: number) => {
    if (!budget) return "N/A";
    return new Intl.NumberFormat("pt-PT", {
      style: "currency",
      currency: "EUR",
    }).format(budget);
  };

  const handleIncentiveClick = (incentiveId: number) => {
    setSelectedIncentiveId(incentiveId);
    setIsIncentiveModalOpen(true);
  };

  const closeIncentiveModal = () => {
    setIsIncentiveModalOpen(false);
    setSelectedIncentiveId(null);
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-gradient-to-br from-amber-600 to-orange-600 rounded-xl">
            <Award className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-slate-800">Incentivos Públicos</h1>
            <p className="text-slate-600 mt-1">
              Explore os incentivos disponíveis em Portugal
            </p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="mt-6 relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Pesquisar por título, setor ou região..."
            className="pl-12 h-12 border-slate-200 rounded-xl bg-slate-50 focus:bg-white focus:ring-2 focus:ring-amber-500 focus:border-transparent transition-all duration-200"
          />
        </div>
      </div>

      {/* Content Area */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {error && (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
            <p className="text-red-600 font-medium">{error}</p>
          </div>
        )}

        {isLoading && (
          <div className="text-center py-12">
            <div className="inline-flex items-center gap-3">
              <Loader2 className="w-6 h-6 text-slate-600 animate-spin" />
              <span className="text-slate-600 font-medium">A carregar incentivos...</span>
            </div>
          </div>
        )}

        {!isLoading && !error && incentives.length === 0 && (
          <div className="text-center py-12">
            <FolderOpen className="w-12 h-12 text-slate-400 mx-auto mb-3" />
            <p className="text-slate-600 font-medium">Nenhum incentivo encontrado</p>
            <p className="text-slate-500 text-sm mt-1">Tente ajustar os critérios de pesquisa</p>
          </div>
        )}

        {incentives.length > 0 && (() => {
          // Pagination logic
          const totalPages = Math.ceil(incentives.length / ITEMS_PER_PAGE);
          const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
          const endIndex = startIndex + ITEMS_PER_PAGE;
          const paginatedIncentives = incentives.slice(startIndex, endIndex);

          return (
          <div className="p-6">
            {/* Results count */}
            <div className="mb-4 text-sm text-slate-600">
              A mostrar {startIndex + 1}-{Math.min(endIndex, incentives.length)} de {incentives.length} incentivos
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {paginatedIncentives.map((incentive) => (
                <Card 
                  key={incentive.id} 
                  className="flex flex-col hover:shadow-lg transition-shadow duration-200 border-slate-200 cursor-pointer"
                  onClick={() => handleIncentiveClick(incentive.id)}
                >
                  <CardHeader>
                    <CardTitle className="text-lg leading-tight text-slate-800 hover:text-amber-600 transition-colors duration-200">
                      {incentive.title}
                    </CardTitle>
                    {incentive.ai_description_structured?.objective && (
                      <CardDescription className="line-clamp-2 text-slate-600 mt-2">
                        {incentive.ai_description_structured.objective}
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col gap-4">
                    {incentive.ai_description_structured?.sectors && incentive.ai_description_structured.sectors.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {incentive.ai_description_structured.sectors.slice(0, 3).map((sector, idx) => (
                          <span
                            key={idx}
                            className="text-xs bg-amber-50 text-amber-700 px-3 py-1 rounded-full font-medium border border-amber-200"
                          >
                            {sector}
                          </span>
                        ))}
                        {incentive.ai_description_structured.sectors.length > 3 && (
                          <span className="text-xs text-slate-500 px-2 py-1">
                            +{incentive.ai_description_structured.sectors.length - 3} mais
                          </span>
                        )}
                      </div>
                    )}

                    <div className="space-y-3 text-sm">
                      {incentive.date_start && (
                        <div className="flex items-center gap-3 text-slate-600">
                          <Calendar className="w-4 h-4 flex-shrink-0 text-slate-400" />
                          <span className="truncate">
                            {formatDate(incentive.date_start)} - {formatDate(incentive.date_end)}
                          </span>
                        </div>
                      )}

                      {incentive.total_budget && (
                        <div className="flex items-center gap-3 text-slate-600">
                          <DollarSign className="w-4 h-4 flex-shrink-0 text-slate-400" />
                          <span className="font-medium text-slate-800">{formatBudget(incentive.total_budget)}</span>
                        </div>
                      )}
                    </div>

                    {incentive.source_link && (
                      <a
                        href={incentive.source_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-2 text-sm text-slate-700 hover:text-slate-900 bg-slate-50 hover:bg-slate-100 px-3 py-2 rounded-lg border border-slate-200 hover:border-slate-300 transition-all duration-200 mt-auto group"
                      >
                        <ExternalLink className="w-4 h-4 group-hover:scale-110 transition-transform" />
                        <span className="font-medium">Ver detalhes</span>
                      </a>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Pagination controls */}
            {totalPages > 1 && (
              <div className="mt-8 flex items-center justify-center gap-2">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Anterior
                </button>

                <div className="flex gap-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
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
                  ))}
                </div>

                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Próxima
                </button>
              </div>
            )}
          </div>
          );
        })()}
      </div>

      {/* Modal */}
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
