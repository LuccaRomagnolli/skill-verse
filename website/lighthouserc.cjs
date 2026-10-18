module.exports = {
  ci: {
    collect: {
      url: ['http://127.0.0.1:8787/'],
      startServerCommand: 'npm run start',
      startServerReadyPattern: 'Ready on',
      numberOfRuns: 3,
      settings: { chromeFlags: '--headless --no-sandbox' },
    },
    assert: {
      assertions: {
        'categories:performance': ['error', { minScore: 0.8 }],
        'categories:accessibility': ['error', { minScore: 0.95 }],
        'categories:best-practices': ['error', { minScore: 0.95 }],
        'categories:seo': ['error', { minScore: 0.95 }],
        'document-title': 'error',
        'meta-description': 'error',
        'http-status-code': 'error',
      },
    },
    upload: { target: 'filesystem', outputDir: './.lighthouseci/reports' },
  },
};
