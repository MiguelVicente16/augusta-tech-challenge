# Frontend - Sistema de Incentivos Públicos

Modern React + TypeScript frontend for the Portuguese Public Incentives System.

## 🎨 Tech Stack

- **React 19** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS v4** - Styling with @theme
- **React Router** - Client-side routing
- **Lucide React** - Icon library
- **shadcn/ui-inspired components** - UI components

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## 📁 Project Structure

```
src/
├── api/              # API client for backend communication
├── components/
│   └── ui/          # Reusable UI components (Button, Input, Card, etc.)
├── lib/             # Utility functions
├── pages/           # Page components
│   ├── ChatbotPage.tsx
│   ├── IncentivesPage.tsx
│   ├── CompaniesPage.tsx
│   └── MatchesPage.tsx
├── types/           # TypeScript type definitions
├── App.tsx          # Main app with routing
├── main.tsx         # App entry point
└── index.css        # Global styles with Tailwind
```

## 🌐 Pages

### 1. Chatbot (`/`)
- Real-time streaming chat interface
- Message history
- Clean conversation UI with user/assistant avatars

### 2. Incentivos (`/incentives`)
- Grid view of all incentives
- Search functionality
- Display: title, sectors, budget, dates
- External links to source

### 3. Empresas (`/companies`)
- Grid view of all companies
- Search by name/description
- Display: name, CAE, description, website

### 4. Correspondências (`/matches`)
- Top 5 companies per incentive
- Score visualization with colors
- Detailed breakdown: strategic fit, quality, execution capacity

## 🎨 Design System

### Colors (Minimalist B&W)
- **Background**: `#FFFFFF` (white)
- **Foreground**: `#000000` (black)
- **Card**: `#FAFAFA` (very light gray)
- **Border**: `#E5E5E5` (light gray)
- **Muted**: `#737373` (medium gray)

### Components
All components follow a minimalist design:
- Sharp borders with subtle shadows
- Black and white color scheme
- Clear typography hierarchy
- Responsive grid layouts

## 🔌 API Integration

The frontend connects to the FastAPI backend via the API client in `src/api/client.ts`.

### Environment Variables

Create a `.env` file:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

### API Client Usage

```typescript
import { apiClient } from "./api/client";

// Get incentives
const incentives = await apiClient.getIncentives({ limit: 50 });

// Get companies
const companies = await apiClient.getCompanies({ search: "tech" });

// Get matches
const matches = await apiClient.getTopMatchesForIncentive(1);

// Send chat message (streaming)
const stream = await apiClient.sendMessage("Hello", history);
```

## 📦 Build

```bash
# Production build
npm run build

# Output will be in dist/
ls dist/
# dist/
# ├── assets/
# │   ├── index-[hash].css
# │   └── index-[hash].js
# └── index.html
```

## 🧪 Development

### Code Quality

```bash
# Lint code
npm run lint

# Type check
npx tsc --noEmit
```

### Adding New Pages

1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`
3. Add navigation link in header

### Adding New Components

1. Create component in `src/components/ui/`
2. Use `cn()` utility for className merging
3. Forward refs for accessibility

Example:

```typescript
import { cn } from "../../lib/utils";

export const MyComponent = ({ className, ...props }) => {
  return (
    <div className={cn("base-styles", className)} {...props} />
  );
};
```

## 🎯 Features

- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Real-time streaming responses
- ✅ Search and filtering
- ✅ Clean, minimalist UI
- ✅ Type-safe with TypeScript
- ✅ Fast builds with Vite
- ✅ Modern React patterns (hooks, context)

## 🚧 Future Improvements

- [ ] Pagination for large datasets
- [ ] Advanced filters
- [ ] Dark mode
- [ ] Export functionality
- [ ] Authentication
- [ ] Offline support

## 📝 Notes

- Uses Tailwind CSS v4 with `@theme` configuration
- All dates formatted in Portuguese locale
- Currency formatted as EUR
- Full-text search via backend API
- Streaming responses for chatbot

## 🤝 Contributing

Follow these guidelines:
- Use TypeScript for all new code
- Follow existing component patterns
- Keep components small and focused
- Use semantic HTML
- Ensure responsive design
