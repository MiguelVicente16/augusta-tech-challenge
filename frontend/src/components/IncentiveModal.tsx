import { useState, useEffect } from "react";
import { X, Calendar, DollarSign, ExternalLink, MapPin, Target, Loader2, FileText, Hash, Building, Clock } from "lucide-react";
import { apiClient } from "../api/client";
import type { Incentive } from "../types";

interface IncentiveModalProps {
  incentiveId: number;
  isOpen: boolean;
  onClose: () => void;
}

export function IncentiveModal({ incentiveId, isOpen, onClose }: IncentiveModalProps) {
  const [incentive, setIncentive] = useState<Incentive | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && incentiveId) {
      loadIncentive();
    }
  }, [isOpen, incentiveId]);

  const loadIncentive = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Fetch single incentive by ID using the correct API method
      const data = await apiClient.getIncentive(incentiveId);
      setIncentive(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar incentivo");
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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-slate-800 to-slate-700 text-white p-6 flex items-start justify-between">
          <div className="flex-1">
            <h2 className="text-2xl font-bold mb-1">
              {isLoading ? "A carregar..." : incentive?.title || "Detalhes do Incentivo"}
            </h2>
            {incentive?.status && (
              <span className={`inline-block px-3 py-1 text-xs font-semibold rounded-full ${
                incentive.status === "Active" ? "bg-green-500" : "bg-gray-500"
              }`}>
                {incentive.status}
              </span>
            )}
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

          {incentive && (
            <div className="space-y-6">
              {/* Program Information */}
              {(incentive.incentive_program || incentive.incentive_project_id) && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <h3 className="text-lg font-semibold text-blue-800 mb-3 flex items-center gap-2">
                    <Hash className="w-5 h-5" />
                    Informação do Programa
                  </h3>
                  <div className="grid md:grid-cols-2 gap-3">
                    {incentive.incentive_program && (
                      <div>
                        <p className="text-xs font-medium text-blue-600 mb-1">Programa</p>
                        <p className="text-blue-900 font-semibold">{incentive.incentive_program}</p>
                      </div>
                    )}
                    {incentive.incentive_project_id && (
                      <div>
                        <p className="text-xs font-medium text-blue-600 mb-1">ID do Projeto</p>
                        <p className="text-blue-900 font-mono text-sm">{incentive.incentive_project_id}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Objective */}
              {incentive.ai_description_structured?.objective && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 mb-2 flex items-center gap-2">
                    <Target className="w-5 h-5 text-slate-600" />
                    Objetivo
                  </h3>
                  <p className="text-slate-700 leading-relaxed">
                    {incentive.ai_description_structured.objective}
                  </p>
                </div>
              )}

              {/* Description */}
              {incentive.description && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 mb-2">Descrição</h3>
                  <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">
                    {incentive.description}
                  </p>
                </div>
              )}

              {/* AI Enhanced Description */}
              {incentive.ai_description && incentive.ai_description !== incentive.description && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 mb-2">Descrição Detalhada</h3>
                  <p className="text-slate-700 leading-relaxed whitespace-pre-wrap">
                    {incentive.ai_description}
                  </p>
                </div>
              )}

              {/* Sectors */}
              {incentive.ai_description_structured?.sectors && incentive.ai_description_structured.sectors.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 mb-3">Setores</h3>
                  <div className="flex flex-wrap gap-2">
                    {incentive.ai_description_structured.sectors.map((sector, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-sm font-medium"
                      >
                        {sector}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Regions */}
              {incentive.ai_description_structured?.regions && incentive.ai_description_structured.regions.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 mb-3 flex items-center gap-2">
                    <MapPin className="w-5 h-5 text-slate-600" />
                    Regiões
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {incentive.ai_description_structured.regions.map((region, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1.5 bg-blue-50 text-blue-700 border border-blue-200 rounded-full text-sm font-medium"
                      >
                        {region}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Activities and Focus Areas */}
              {incentive.ai_description_structured?.activities && incentive.ai_description_structured.activities.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 mb-3">Atividades</h3>
                  <div className="flex flex-wrap gap-2">
                    {incentive.ai_description_structured.activities.map((activity, idx) => (
                      <span
                        key={idx}
                        className="px-3 py-1.5 bg-green-50 text-green-700 border border-green-200 rounded-full text-sm font-medium"
                      >
                        {activity}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Dates and Budget */}
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {incentive.date_publication && (
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                    <div className="flex items-center gap-3 text-slate-700">
                      <Clock className="w-5 h-5 text-slate-500" />
                      <div>
                        <p className="text-xs font-medium text-slate-500 mb-1">Data de Publicação</p>
                        <p className="font-semibold">{formatDate(incentive.date_publication)}</p>
                      </div>
                    </div>
                  </div>
                )}

                {incentive.date_start && (
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                    <div className="flex items-center gap-3 text-slate-700">
                      <Calendar className="w-5 h-5 text-slate-500" />
                      <div>
                        <p className="text-xs font-medium text-slate-500 mb-1">Período de Candidatura</p>
                        <p className="font-semibold">
                          {formatDate(incentive.date_start)} - {formatDate(incentive.date_end)}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {incentive.total_budget && (
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                    <div className="flex items-center gap-3 text-slate-700">
                      <DollarSign className="w-5 h-5 text-slate-500" />
                      <div>
                        <p className="text-xs font-medium text-slate-500 mb-1">Orçamento Total</p>
                        <p className="font-semibold text-lg">{formatBudget(incentive.total_budget)}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Eligibility Criteria */}
              {incentive.eligibility_criteria && Object.keys(incentive.eligibility_criteria).length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 mb-3 flex items-center gap-2">
                    <Building className="w-5 h-5 text-slate-600" />
                    Critérios de Elegibilidade
                  </h3>
                  <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
                    {Object.entries(incentive.eligibility_criteria).map(([key, value], idx) => (
                      <div key={idx} className="mb-2 last:mb-0">
                        <span className="font-medium text-orange-800 capitalize">
                          {key.replace(/_/g, ' ')}:
                        </span>
                        <span className="ml-2 text-orange-700">
                          {typeof value === 'string' ? value : JSON.stringify(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Requirements */}
              {incentive.ai_description_structured?.requirements && incentive.ai_description_structured.requirements.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 mb-3">Requisitos</h3>
                  <ul className="space-y-2">
                    {incentive.ai_description_structured.requirements.map((req, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-slate-700">
                        <span className="w-1.5 h-1.5 bg-slate-400 rounded-full mt-2 flex-shrink-0"></span>
                        <span>{req}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Documents */}
              {((incentive.document_urls && incentive.document_urls.length > 0) || 
                (incentive.gcs_document_urls && incentive.gcs_document_urls.length > 0)) && (
                <div>
                  <h3 className="text-lg font-semibold text-slate-800 mb-3 flex items-center gap-2">
                    <FileText className="w-5 h-5 text-slate-600" />
                    Documentos
                  </h3>
                  <div className="space-y-2">
                    {incentive.document_urls?.map((doc, idx) => (
                      <div key={idx} className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
                        <FileText className="w-4 h-4 text-slate-500" />
                        <span className="text-slate-700 text-sm">
                          {typeof doc === 'object' ? doc.name || doc.type || `Documento ${idx + 1}` : `Documento ${idx + 1}`}
                        </span>
                      </div>
                    ))}
                    {incentive.gcs_document_urls?.map((url, idx) => (
                      <a 
                        key={idx} 
                        href={url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 p-3 bg-slate-50 rounded-lg border border-slate-200 hover:bg-slate-100 transition-colors"
                      >
                        <FileText className="w-4 h-4 text-slate-500" />
                        <span className="text-slate-700 text-sm">Documento {idx + 1}</span>
                        <ExternalLink className="w-3 h-3 text-slate-400 ml-auto" />
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Additional Metadata */}
              {(incentive.project_id || incentive.created_at || incentive.updated_at) && (
                <div className="border-t border-slate-200 pt-4">
                  <h3 className="text-lg font-semibold text-slate-800 mb-3">Informações Técnicas</h3>
                  <div className="grid md:grid-cols-2 gap-3 text-sm">
                    {incentive.project_id && (
                      <div>
                        <span className="font-medium text-slate-600">ID do Projeto:</span>
                        <span className="ml-2 text-slate-700 font-mono">{incentive.project_id}</span>
                      </div>
                    )}
                    <div>
                      <span className="font-medium text-slate-600">ID do Sistema:</span>
                      <span className="ml-2 text-slate-700 font-mono">{incentive.id}</span>
                    </div>
                    {incentive.created_at && (
                      <div>
                        <span className="font-medium text-slate-600">Criado em:</span>
                        <span className="ml-2 text-slate-700">{formatDate(incentive.created_at)}</span>
                      </div>
                    )}
                    {incentive.updated_at && (
                      <div>
                        <span className="font-medium text-slate-600">Atualizado em:</span>
                        <span className="ml-2 text-slate-700">{formatDate(incentive.updated_at)}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Source Link */}
              {incentive.source_link && (
                <div className="pt-4 border-t border-slate-200">
                  <a
                    href={incentive.source_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-3 bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition-colors font-medium"
                  >
                    <ExternalLink className="w-5 h-5" />
                    Ver página oficial
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
