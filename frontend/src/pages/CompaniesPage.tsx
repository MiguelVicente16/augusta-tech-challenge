import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, Building2, Globe, AlertCircle, Loader2, FolderOpen } from "lucide-react";
import { Input } from "../components/ui/input";
import { CompanyModal } from "../components/CompanyModal";
import { apiClient } from "../api/client";
import type { Company } from "../types";

export function CompaniesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [isCompanyModalOpen, setIsCompanyModalOpen] = useState(false);

  const ITEMS_PER_PAGE = 10;

  // Update search from URL params on mount
  useEffect(() => {
    const urlSearch = searchParams.get("search");
    const urlId = searchParams.get("id");

    if (urlSearch) {
      setSearch(urlSearch);
    } else if (urlId) {
      // If ID is provided, search for that specific company
      setSearch(urlId);
    }
  }, [searchParams]);

  useEffect(() => {
    loadCompanies();
  }, [search]);

  const loadCompanies = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.getCompanies({
        search: search || undefined,
        limit: 50,
      });
      setCompanies(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar empresas");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompanyClick = (companyId: number) => {
    setSelectedCompanyId(companyId);
    setIsCompanyModalOpen(true);
  };

  const closeCompanyModal = () => {
    setIsCompanyModalOpen(false);
    setSelectedCompanyId(null);
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-gradient-to-br from-slate-800 to-slate-600 rounded-xl">
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-slate-800">Empresas</h1>
            <p className="text-slate-600 mt-1">
              Explore as empresas cadastradas no sistema
            </p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="mt-6 relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Pesquisar empresas por nome, setor ou descrição..."
            className="pl-12 h-12 border-slate-200 rounded-xl bg-slate-50 focus:bg-white focus:ring-2 focus:ring-slate-500 focus:border-transparent transition-all duration-200"
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
              <span className="text-slate-600 font-medium">A carregar empresas...</span>
            </div>
          </div>
        )}

        {!isLoading && !error && companies.length === 0 && (
          <div className="text-center py-12">
            <FolderOpen className="w-12 h-12 text-slate-400 mx-auto mb-3" />
            <p className="text-slate-600 font-medium">Nenhuma empresa encontrada</p>
            <p className="text-slate-500 text-sm mt-1">Tente ajustar os critérios de pesquisa</p>
          </div>
        )}

        {companies.length > 0 && (() => {
          // Pagination logic
          const totalPages = Math.ceil(companies.length / ITEMS_PER_PAGE);
          const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
          const endIndex = startIndex + ITEMS_PER_PAGE;
          const paginatedCompanies = companies.slice(startIndex, endIndex);

          return (
          <div className="p-6">
            {/* Results count */}
            <div className="mb-4 text-sm text-slate-600">
              A mostrar {startIndex + 1}-{Math.min(endIndex, companies.length)} de {companies.length} empresas
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {paginatedCompanies.map((company) => (
                <div 
                  key={company.id} 
                  className="bg-slate-50 rounded-xl border border-slate-200 hover:border-slate-300 transition-all duration-200 hover:shadow-md cursor-pointer"
                  onClick={() => handleCompanyClick(company.id)}
                >
                  <div className="p-6">
                    <div className="flex items-start gap-4 mb-4">
                      <div className="p-2 bg-slate-200 rounded-lg">
                        <Building2 className="w-5 h-5 text-slate-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-slate-800 text-lg leading-tight hover:text-slate-600 transition-colors duration-200">
                          {company.company_name}
                        </h3>
                        {company.cae_primary_label && (
                          <p className="text-sm text-slate-600 mt-1">{company.cae_primary_label}</p>
                        )}
                      </div>
                    </div>
                    
                    {company.trade_description_native && (
                      <p className="text-sm text-slate-600 line-clamp-3 mb-4 leading-relaxed">
                        {company.trade_description_native}
                      </p>
                    )}

                    {company.website && (
                      <a
                        href={company.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex items-center gap-2 text-sm text-slate-700 hover:text-slate-900 bg-white px-3 py-2 rounded-lg border border-slate-200 hover:border-slate-300 transition-all duration-200"
                      >
                        <Globe className="w-4 h-4" />
                        <span className="font-medium">Website</span>
                      </a>
                    )}
                  </div>
                </div>
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
      {selectedCompanyId && (
        <CompanyModal
          companyId={selectedCompanyId}
          isOpen={isCompanyModalOpen}
          onClose={closeCompanyModal}
        />
      )}
    </div>
  );
}
