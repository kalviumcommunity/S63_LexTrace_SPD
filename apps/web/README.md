# ChronoLex Web Application (`apps/web`)

Next.js frontend interface for the ChronoLex regulatory compliance assistant.

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Design Principles**: Dark-mode primary, accessible contrast, responsive layout

## Current Phase (Sprint #2 - Step 1)

This frontend currently serves as the initial verification interface displaying:
- Project branding and tagline: *"Find the rule. Know when it applied. See why."*
- System mission and target user overview for bank compliance officers.
- Operational status confirmation.

*Note: The interactive chat UI, document upload, and citation panels will be introduced in subsequent roadmap phases.*

## Local Development

```bash
# Navigate to web application directory
cd apps/web

# Install dependencies (if not already installed)
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Build and Test

```bash
# Type check and production build
npm run build

# Code linting
npm run lint
```
