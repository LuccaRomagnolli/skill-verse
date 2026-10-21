import { env } from 'cloudflare:workers';
import { publicOrigin } from '@/lib/security';
import html from '../../server/store.html?raw';
export function GET(request: Request) {
  const origin = publicOrigin(env.SITE_ORIGIN);
  const pathname = new URL(request.url).pathname;
  const canonical = origin ? `<link rel="canonical" href="${origin}${pathname}" /><meta property="og:url" content="${origin}${pathname}" />` : '';
  return new Response(html.replace('</head>', `  ${canonical}\n</head>`), { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } });
}
