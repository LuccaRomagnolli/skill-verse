declare namespace Cloudflare {
  interface Env {
    DB?: D1Database;
    BUCKET?: R2Bucket;
    SYNCPAY_CLIENT_ID?: string;
    SYNCPAY_CLIENT_SECRET?: string;
    SYNCPAY_PUBLIC_KEY?: string;
    SYNCPAY_WEBHOOK_TOKEN?: string;
    PAYMENTS_ENABLED?: string;
    PACK_OBJECT_KEY?: string;
    RELEASE_UPLOAD_TOKEN?: string;
    SITE_ORIGIN?: string;
  }
}
