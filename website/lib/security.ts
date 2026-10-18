// Dynamic responses pass through this Worker boundary. Static assets use
// public/_headers because Cloudflare can serve them before fetch runs.
const contentSecurityPolicy = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'self'",
  "script-src 'self'",
  "style-src 'self' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com",
  "img-src 'self' data: blob:",
  "connect-src 'self' https://api.syncpayments.com.br",
].join('; ');

export function publicOrigin(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && url.origin === value ? url.origin : null;
  } catch {
    return null;
  }
}

export function secureResponse(request: Request, response: Response): Response {
  const headers = new Headers(response.headers);
  headers.set('X-Content-Type-Options', 'nosniff');
  headers.set('X-Frame-Options', 'DENY');
  headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=()');
  headers.set('X-XSS-Protection', '0');
  if (new URL(request.url).protocol === 'https:') {
    headers.set('Strict-Transport-Security', 'max-age=31536000');
  }
  if (headers.get('content-type')?.toLowerCase().includes('text/html')) {
    headers.set('Content-Security-Policy', contentSecurityPolicy);
  }
  if (new URL(request.url).pathname.startsWith('/api/')) {
    headers.set('Cache-Control', 'no-store');
  }
  return new Response(response.body, {status: response.status, statusText: response.statusText, headers});
}
