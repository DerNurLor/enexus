/** @type {import('next').NextConfig} */
const withPWA = require('@ducanh2912/next-pwa').default({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === 'development',
  output: 'standalone',
  fallbacks: {
    document: '/offline',
  },
  workboxOptions: {
    runtimeCaching: [
      {
        // Страница профиля — всегда только сеть, без кеша (динамичный контент)
        urlPattern: /\/profile$/,
        handler: 'NetworkOnly',
      },
      {
        urlPattern: /\/schedule?$/,
        handler: 'NetworkFirst',
        options: {
          cacheName: 'pages-cache',
          networkTimeoutSeconds: 5,
          expiration: { maxEntries: 10, maxAgeSeconds: 7 * 24 * 60 * 60 },
        },
      },
      {
        urlPattern: /\/api\/schedules\/.+\/day/,
        handler: 'StaleWhileRevalidate',
        options: {
          cacheName: 'schedule-api-cache',
          expiration: { maxEntries: 100, maxAgeSeconds: 24 * 60 * 60 },
        },
      },
      {
        urlPattern: /\/api\/search\//,
        handler: 'NetworkFirst',
        options: {
          cacheName: 'search-api-cache',
          networkTimeoutSeconds: 3,
          expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 },
        },
      },
      {
        urlPattern: /\/_next\/static\/.*/,
        handler: 'CacheFirst',
        options: {
          cacheName: 'next-static-cache',
          expiration: { maxEntries: 200, maxAgeSeconds: 30 * 24 * 60 * 60 },
        },
      },
      {
        urlPattern: /\.(png|jpg|jpeg|svg|ico|woff2?|ttf)$/,
        handler: 'CacheFirst',
        options: {
          cacheName: 'assets-cache',
          expiration: { maxEntries: 50, maxAgeSeconds: 30 * 24 * 60 * 60 },
        },
      },
    ],
  },
})

const nextConfig = {
  reactStrictMode: false,
}

module.exports = withPWA(nextConfig)
