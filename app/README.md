# Lang2Query Frontend

🎨 **Modern Next.js Frontend** for Lang2Query - A beautiful, responsive web interface for natural language to SQL conversion with real-time AI-powered processing.

[![Next.js](https://img.shields.io/badge/Next.js-15.5.4-black.svg)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19.0.0-blue.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7.2-blue.svg)](https://www.typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind%20CSS-3.4.17-38B2AC.svg)](https://tailwindcss.com)

## ✨ Features

### 🎨 Modern User Interface

- **TypeScript**: Full type safety with comprehensive type definitions
- **Responsive Design**: Clean, modern interface that works on all devices
- **Dark/Light Mode**: Automatic theme switching based on system preferences
- **Component Library**: Reusable, well-documented React components

### 📡 Real-time Communication

- **WebSocket Integration**: Live workflow progress tracking with real-time updates
- **Interactive Mode**: Step-by-step query processing visualization
- **Live State Display**: Watch as databases, tables, and columns are identified
- **Progress Indicators**: Beautiful loading states and progress bars

### 🛠️ Developer Experience

- **Hot Reload**: Instant development feedback with Next.js dev server
- **ESLint**: Comprehensive code quality enforcement
- **TypeScript**: Full type safety and IntelliSense support
- **Component Architecture**: Modular, reusable component design

### 🚀 Performance

- **Server-Side Rendering**: Fast initial page loads with Next.js SSR
- **Code Splitting**: Automatic code splitting for optimal bundle sizes
- **Optimized Images**: Next.js Image component for optimal performance
- **Caching**: Intelligent caching strategies for API calls

## Tech Stack

- **Framework**: Next.js 15.5.4 with App Router
- **React**: React 19.0.0 with React DOM 19.0.0
- **Language**: TypeScript 5.7.2
- **Styling**: Tailwind CSS 3.4.17
- **Icons**: Lucide React 0.468.0
- **HTTP Client**: Axios 1.7.9
- **Code Quality**: ESLint 9.17.0 with TypeScript rules

## 🚀 Getting Started

### Prerequisites

- **Node.js 18+** (recommended: Node.js 20+)
- **npm** or **yarn** package manager
- **Lang2Query Backend** running on `http://localhost:8000`

### Installation

1. **Navigate to the frontend directory:**

   ```bash
   cd app
   ```

2. **Install dependencies:**

   ```bash
   npm install
   # or
   yarn install
   ```

3. **Start development server:**

   ```bash
   npm run dev
   # or
   yarn dev
   ```

4. **Open [http://localhost:3000](http://localhost:3000) in your browser**

### Quick Start with Backend

If you want to run both frontend and backend together:

```bash
# From the project root
make run
```

This will start both the FastAPI backend (`http://localhost:8000`) and Next.js frontend (`http://localhost:3000`) simultaneously.

## 📁 Project Structure

```
app/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── globals.css         # Global styles and Tailwind imports
│   │   ├── layout.tsx          # Root layout component
│   │   └── page.tsx            # Home page component
│   ├── components/             # React components
│   │   ├── ChatContainer/      # Chat interface container
│   │   │   ├── ChatContainer.tsx
│   │   │   └── index.ts
│   │   ├── ChatMessage/        # Individual chat message
│   │   │   ├── ChatMessage.tsx
│   │   │   └── index.ts
│   │   ├── Header/             # Application header
│   │   │   ├── Header.tsx
│   │   │   └── index.ts
│   │   ├── LiveStateDisplay/   # Real-time state visualization
│   │   │   ├── LiveStateDisplay.tsx
│   │   │   └── index.ts
│   │   ├── MarkdownRenderer/   # Markdown content rendering
│   │   │   ├── MarkdownRenderer.tsx
│   │   │   └── index.ts
│   │   ├── ProgressIndicator/  # Progress tracking component
│   │   │   ├── ProgressIndicator.tsx
│   │   │   └── index.ts
│   │   ├── QueryForm/          # Query input form
│   │   │   ├── QueryForm.tsx
│   │   │   └── index.ts
│   │   ├── QueryInput/         # Query input component
│   │   │   ├── QueryInput.tsx
│   │   │   └── index.ts
│   │   ├── QueryInterface/     # Main query interface
│   │   │   ├── QueryInterface.tsx
│   │   │   └── index.ts
│   │   ├── ResultsDisplay/     # Results presentation
│   │   │   ├── ResultsDisplay.tsx
│   │   │   └── index.ts
│   │   ├── SelectionReviewCard/ # Selection review component
│   │   │   ├── SelectionReviewCard.tsx
│   │   │   └── index.ts
│   │   ├── Sidebar/            # Application sidebar
│   │   │   ├── Sidebar.tsx
│   │   │   └── index.ts
│   │   ├── StatusPanel/        # Status information panel
│   │   │   ├── StatusPanel.tsx
│   │   │   └── index.ts
│   │   └── index.ts            # Component exports
│   ├── hooks/                  # Custom React hooks
│   │   └── useSystemStatus.ts  # System status hook
│   ├── lib/                    # Utilities and API client
│   │   ├── api.ts              # API client and HTTP utilities
│   │   ├── toast.ts            # Toast notification utilities
│   │   └── websocket.ts        # WebSocket client
│   ├── styles/                 # Styling
│   │   └── globals.css         # Global CSS and Tailwind
│   └── types/                  # TypeScript type definitions
│       └── index.ts            # Shared types and interfaces
├── package.json                # Dependencies and scripts
├── tsconfig.json              # TypeScript configuration
├── tailwind.config.js         # Tailwind CSS configuration
├── postcss.config.js          # PostCSS configuration
├── next.config.js             # Next.js configuration
└── eslint.config.js           # ESLint configuration
```

## 🛠️ Scripts

| Command              | Description                              |
| -------------------- | ---------------------------------------- |
| `npm run dev`        | Start development server with hot reload |
| `npm run build`      | Build optimized production bundle        |
| `npm run start`      | Start production server                  |
| `npm run lint`       | Run ESLint for code quality checks       |
| `npm run type-check` | Run TypeScript type checking             |
| `npm run clean`      | Clean build artifacts and cache          |

## 🔌 API Integration

The frontend communicates with the Lang2Query backend via REST API and WebSocket connections.

### Configuration

Configure the backend URL in `next.config.js`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*", // Backend API
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/ws/:path*",
        destination: "ws://localhost:8000/ws/:path*", // WebSocket connection
      },
    ];
  },
};

module.exports = nextConfig;
```

### API Client

The frontend uses a centralized API client (`lib/api.ts`) for all backend communication:

```typescript
// Example API usage
import { apiClient } from "@/lib/api";

// Process a query
const response = await apiClient.processQuery({
  query: "Show me all users with pending verification",
  mode: "interactive",
});

// Stream query processing
const stream = apiClient.streamQuery(query);
```

### WebSocket Integration

Real-time updates are handled via WebSocket connections:

```typescript
// WebSocket usage
import { useWebSocket } from "@/lib/websocket";

const { sendMessage, lastMessage, readyState } = useWebSocket(
  "ws://localhost:8000/ws/query",
);
```

## 🧪 Development

### Code Quality Standards

- **TypeScript First**: Use TypeScript for all new code with strict type checking
- **ESLint Compliance**: Follow configured ESLint rules for consistent code style
- **Component Architecture**: Keep components modular, reusable, and focused on single responsibilities
- **Error Handling**: Implement comprehensive error handling with user-friendly messages
- **Testing**: Write unit tests for components and utilities
- **Documentation**: Document complex logic and component APIs

### Component Guidelines

- **Functional Components**: Use functional components with React hooks
- **TypeScript Interfaces**: Define proper interfaces for all props and state
- **Single Responsibility**: Each component should have one clear purpose
- **Styling**: Use Tailwind CSS utility classes for consistent styling
- **Performance**: Optimize with React.memo, useMemo, and useCallback when appropriate
- **Accessibility**: Follow WCAG guidelines for accessible components

### Development Workflow

1. **Create Feature Branch**: `git checkout -b feature/component-name`
2. **Develop Component**: Follow component guidelines and TypeScript best practices
3. **Test Component**: Write tests and ensure all functionality works
4. **Lint & Type Check**: Run `npm run lint` and `npm run type-check`
5. **Commit Changes**: Use conventional commit messages
6. **Create Pull Request**: Submit PR with detailed description

## 🚀 Deployment

### Production Build

```bash
# Build optimized production bundle
npm run build

# Start production server
npm run start
```

### Docker Deployment

```dockerfile
FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM base AS build
RUN npm ci
COPY . .
RUN npm run build

FROM base AS runtime
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
COPY --from=build /app/package*.json ./
EXPOSE 3000
CMD ["npm", "start"]
```

### Environment Variables

Configure production environment variables:

```bash
# .env.production
NEXT_PUBLIC_API_URL=https://your-backend-api.com
NEXT_PUBLIC_WS_URL=wss://your-backend-api.com/ws
```

### Performance Optimization

- **Bundle Analysis**: Use `npm run analyze` to analyze bundle size
- **Image Optimization**: Use Next.js Image component for optimized images
- **Code Splitting**: Leverage Next.js automatic code splitting
- **Caching**: Implement proper caching strategies for API calls

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes following the development guidelines
4. Add tests for new functionality
5. Run the test suite: `npm run test`
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.
