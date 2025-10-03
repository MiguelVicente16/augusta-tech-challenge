import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { MessageSquare, TrendingUp, Building2, Award, Menu, X, ChevronLeft, ChevronRight } from "lucide-react";
import { ChatbotPage } from "./pages/ChatbotPage";
import { IncentivesPage } from "./pages/IncentivesPage";
import { CompaniesPage } from "./pages/CompaniesPage";
import { MatchesPage } from "./pages/MatchesPage";
import { useState } from "react";

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <BrowserRouter>
      <div className="flex h-screen bg-gradient-to-br from-slate-50 to-slate-100 overflow-hidden">
        {/* Mobile Overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar */}
        <aside
          className={`fixed lg:static inset-y-0 left-0 z-50 bg-slate-50 border-r border-slate-200 flex flex-col transition-all duration-300 ease-in-out ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
          } ${sidebarCollapsed ? "lg:w-20" : "lg:w-72"} w-72`}
        >
          {/* Sidebar Header */}
          <div className="p-6 border-b border-slate-200/60">
            <div className="flex items-center justify-between mb-4">
              {!sidebarCollapsed && (
                <h1 className="text-xl font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent">
                  Incentivos PT
                </h1>
              )}
              <button
                onClick={() => setSidebarOpen(false)}
                className="lg:hidden p-2 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-600" />
              </button>
            </div>
            {!sidebarCollapsed && (
              <div className="flex items-center gap-2 bg-green-100/50 rounded-lg p-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-xs text-green-700 font-medium">Sistema Online</span>
              </div>
            )}
            {sidebarCollapsed && (
              <div className="flex justify-center">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              </div>
            )}
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
            <NavLink
              to="/"
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                  isActive
                    ? "bg-slate-900 text-white shadow-md"
                    : "text-slate-700 hover:bg-slate-100"
                } ${sidebarCollapsed ? "justify-center" : ""}`
              }
              title={sidebarCollapsed ? "Chatbot" : ""}
            >
              <MessageSquare className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && <span className="font-medium">Chatbot</span>}
            </NavLink>
            <NavLink
              to="/incentives"
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                  isActive
                    ? "bg-slate-900 text-white shadow-md"
                    : "text-slate-700 hover:bg-slate-100"
                } ${sidebarCollapsed ? "justify-center" : ""}`
              }
              title={sidebarCollapsed ? "Incentivos" : ""}
            >
              <Award className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && <span className="font-medium">Incentivos</span>}
            </NavLink>
            <NavLink
              to="/companies"
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                  isActive
                    ? "bg-slate-900 text-white shadow-md"
                    : "text-slate-700 hover:bg-slate-100"
                } ${sidebarCollapsed ? "justify-center" : ""}`
              }
              title={sidebarCollapsed ? "Empresas" : ""}
            >
              <Building2 className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && <span className="font-medium">Empresas</span>}
            </NavLink>
            <NavLink
              to="/matches"
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                  isActive
                    ? "bg-slate-900 text-white shadow-md"
                    : "text-slate-700 hover:bg-slate-100"
                } ${sidebarCollapsed ? "justify-center" : ""}`
              }
              title={sidebarCollapsed ? "Correspondências" : ""}
            >
              <TrendingUp className="w-5 h-5 flex-shrink-0" />
              {!sidebarCollapsed && <span className="font-medium">Correspondências</span>}
            </NavLink>
          </nav>

          {/* Sidebar Footer */}
          <div className="p-4 border-t border-slate-200/60">
            {!sidebarCollapsed ? (
              <div className="text-xs text-slate-500 text-center">
                Sistema de Incentivos Públicos Portugal
              </div>
            ) : (
              <div className="flex justify-center">
                <div className="w-8 h-8 bg-slate-200/50 rounded-lg flex items-center justify-center">
                  <Award className="w-4 h-4 text-slate-600" />
                </div>
              </div>
            )}
          </div>

          {/* Collapse/Expand Toggle - Desktop Only */}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="hidden lg:flex absolute -right-3 top-6 bg-white border border-slate-200 rounded-full p-1.5 hover:bg-slate-100 transition-colors shadow-md z-10"
            title={sidebarCollapsed ? "Expandir sidebar" : "Colapsar sidebar"}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-4 h-4 text-slate-600" />
            ) : (
              <ChevronLeft className="w-4 h-4 text-slate-600" />
            )}
          </button>
        </aside>

        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Mobile Header */}
          <header className="lg:hidden bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <Menu className="w-5 h-5 text-slate-600" />
            </button>
            <h1 className="text-lg font-bold bg-gradient-to-r from-slate-800 to-slate-600 bg-clip-text text-transparent">
              Incentivos PT
            </h1>
          </header>

          {/* Main Content Area */}
          <main className="flex-1 overflow-auto">
            <Routes>
              <Route path="/" element={<ChatbotPage />} />
              <Route
                path="/incentives"
                element={
                  <div className="h-full p-6">
                    <IncentivesPage />
                  </div>
                }
              />
              <Route
                path="/companies"
                element={
                  <div className="h-full p-6">
                    <CompaniesPage />
                  </div>
                }
              />
              <Route
                path="/matches"
                element={
                  <div className="h-full p-6">
                    <MatchesPage />
                  </div>
                }
              />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
