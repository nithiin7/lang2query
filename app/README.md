# Text2Query Frontend

A modern Next.js frontend for Text2Query - Natural Language to SQL conversion with AI-powered precision.

## Features

- **TypeScript**: Full type safety with TypeScript
- **Modern UI**: Clean, responsive interface with Tailwind CSS
- **Real-time Updates**: Live workflow progress tracking
- **Interactive Mode**: Step-by-step query processing visualization
- **Error Handling**: Comprehensive error handling and user feedback
- **ESLint**: Code quality enforcement

## Tech Stack

- **Framework**: Next.js 15.5.4 with App Router
- **React**: React 19.0.0 with React DOM 19.0.0
- **Language**: TypeScript 5.7.2
- **Styling**: Tailwind CSS 3.4.17
- **Icons**: Lucide React 0.468.0
- **HTTP Client**: Axios 1.7.9
- **Code Quality**: ESLint 9.17.0 with TypeScript rules

## Getting Started

1. **Install dependencies:**

   ```bash
   cd app
   npm install
   ```

2. **Start development server:**

   ```bash
   npm run dev
   ```

3. **Open [http://localhost:3000](http://localhost:3000) in your browser**

## Project Structure

```
app/
├── src/
│   ├── app/
│   │   ├── globals.css      # Global styles
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Home page
│   ├── components/
│   │   ├── QueryInterface.tsx     # Main interface component
│   │   ├── QueryForm.tsx          # Query input form
│   │   ├── ProgressIndicator.tsx  # Progress tracking
│   │   ├── LiveStateDisplay.tsx   # Live workflow state
│   │   ├── ResultsDisplay.tsx     # Results presentation
│   │   └── index.ts               # Component exports
│   ├── lib/
│   │   └── api.ts                 # API client and utilities
│   └── types/
│       └── index.ts               # TypeScript type definitions
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── next.config.js
└── eslint.config.js
```

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## API Integration

The frontend communicates with the Python backend via REST API. Configure the backend URL in `next.config.js`:

```javascript
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:8000/api/:path*', // Update this URL
    },
  ]
}
```

## Development

### Code Quality

- Use TypeScript for all new code
- Follow ESLint rules
- Keep components modular and reusable
- Use proper error handling
- Write clear, descriptive commit messages

### Component Guidelines

- Use functional components with hooks
- Implement proper TypeScript interfaces
- Keep components focused on single responsibilities
- Use Tailwind CSS for styling
- Follow React best practices

## Deployment

Build the application for production:

```bash
npm run build
npm run start
```

The application will be available on port 3000 by default.
