import { env } from 'cloudflare:workers';
import { hash, json } from '@/lib/payments';

// Test authentication and a read-only partner request. This never creates a charge.
export async function POST(request: Request) {
  const configured = env.RELEASE_UPLOAD_TOKEN;
  const authorization = request.headers.get('authorization') ?? '';
  const supplied = authorization.startsWith('Bearer ') ? authorization.slice(7) : '';
  if (!configured || configured.length < 32 || !supplied) return json({ error: 'Não autorizado.' }, 401);
  const a = await hash(configured), b = await hash(supplied);
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  if (diff !== 0) return json({ error: 'Não autorizado.' }, 401);
  if (!env.SYNCPAY_CLIENT_ID || !env.SYNCPAY_CLIENT_SECRET) return json({ connected: false, reason: 'missing_credentials' }, 503);
  try {
    const response = await fetch('https://api.syncpayments.com.br/api/partner/v1/auth-token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ client_id: env.SYNCPAY_CLIENT_ID, client_secret: env.SYNCPAY_CLIENT_SECRET }),
      signal: AbortSignal.timeout(15000),
    });
    if (!response.ok) return json({ connected: false, providerStatus: response.status }, 502);
    const data = await response.json() as { access_token?: unknown };
    if (typeof data.access_token !== 'string' || !data.access_token) return json({ connected: false, reason: 'invalid_response' }, 502);
    const profile = await fetch('https://api.syncpayments.com.br/api/partner/v1/profile', {
      headers: { 'Accept': 'application/json', 'Authorization': `Bearer ${data.access_token}` },
      signal: AbortSignal.timeout(15000),
    });
    if (!profile.ok) return json({ connected: true, partnerAccess: false, providerStatus: profile.status }, 502);
    return json({ connected: true, partnerAccess: true });
  } catch {
    return json({ connected: false, reason: 'connection_failed' }, 502);
  }
}
