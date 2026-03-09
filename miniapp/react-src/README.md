# NCFU MiniApp — React TypeScript Source

## Stack
- React 18 + TypeScript
- Vite 5
- Apollo Client (optional GraphQL)

## Development
```bash
npm install
npm run dev
```

## Build
```bash
npm run build
# Copy dist/ contents to miniapp/app/miniapp/static/
```

## Production Deployment
The built `dist/index.html` replaces `miniapp/app/miniapp/templates/index.html`.
For quick deploy without building, use `miniapp-template.html` (pre-built standalone version).
