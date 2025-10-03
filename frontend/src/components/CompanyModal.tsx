import { useState, useEffect } from "react";
import { X, Building2, Globe, Briefcase, Loader2, Hash, Calendar } from "lucide-react";
import { apiClient } from "../api/client";
import type { Company } from "../types";

interface CompanyModalProps {
  companyId: number;
  isOpen: boolean;
  onClose: () => void;
}

export function CompanyModal({ companyId, isOpen, onClose }: CompanyModalProps) {
  const [company, setCompany] = useState<Company | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && companyId) {
      loadCompany();
    }
  }, [isOpen, companyId]);

  const loadCompany = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Fetch single company by ID using the correct API method
      const data = await apiClient.getCompany(companyId);
      setCompany(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar empresa");
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("pt-PT");
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl max-h-[90vh] bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-slate-800 to-slate-700 text-white p-6 flex items-start justify-between">
          <div className="flex items-start gap-4 flex-1">
            <div className="p-3 bg-white/10 rounded-xl">
              <Building2 className="w-8 h-8" />
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-1">
                {isLoading ? "A carregar..." : company?.company_name || "Detalhes da Empresa"}
              </h2>
              {company?.cae_primary_label && (
                <p className="text-slate-200 text-sm">{company.cae_primary_label}</p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-2 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-140px)] p-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-slate-600 animate-spin" />
            </div>
          )}

          {error && (
            <div className="text-center py-12">
              <p className="text-red-600">{error}</p>
            </div>
          )}

          {company && (
            <div className="space-y-6">
              {/* Company Description */}
              {company.trade_description_native && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 mb-3 flex items-center gap-2">
                    <Briefcase className="w-5 h-5 text-slate-600" />
                    Descrição da Atividade
                  </h3>
                  <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">
                    {company.trade_description_native}
                  </p>
                </div>
              )}

              {/* Company Details Grid */}
              <div className="grid md:grid-cols-2 gap-4">
                {/* Sector */}
                {company.cae_primary_label && (
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                    <h3 className="text-sm font-medium text-slate-500 mb-2">Setor Principal (CAE)</h3>
                    <p className="text-slate-800 font-semibold">{company.cae_primary_label}</p>
                  </div>
                )}

                {/* Creation Date */}
                {company.created_at && (
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                    <div className="flex items-center gap-3">
                      <Calendar className="w-5 h-5 text-slate-500" />
                      <div>
                        <h3 className="text-sm font-medium text-slate-500 mb-1">Data de Registo</h3>
                        <p className="text-slate-800 font-semibold">{formatDate(company.created_at)}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Website */}
              {company.website && (
                <div className="pt-4 border-t border-slate-200">
                  <a
                    href={company.website.startsWith('http') ? company.website : `https://${company.website}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-3 bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition-colors font-medium"
                  >
                    <Globe className="w-5 h-5" />
                    Visitar website
                  </a>
                </div>
              )}

              {/* Technical Information */}
              <div className="p-4 bg-blue-50 rounded-xl border border-blue-200">
                <h3 className="text-lg font-semibold text-blue-800 mb-3 flex items-center gap-2">
                  <Hash className="w-5 h-5" />
                  Informações Técnicas
                </h3>
                <div className="grid md:grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="font-medium text-blue-600">ID da Empresa:</span>
                    <span className="ml-2 text-blue-900 font-mono">{company.id}</span>
                  </div>
                  <div>
                    <span className="font-medium text-blue-600">Nome Completo:</span>
                    <span className="ml-2 text-blue-900">{company.company_name}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
