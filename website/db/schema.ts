import { sqliteTable, text, integer, index } from 'drizzle-orm/sqlite-core';
export const orders = sqliteTable('orders', {
  id: text('id').primaryKey(),
  tokenHash: text('token_hash').notNull(),
  ipHash: text('ip_hash').notNull(),
  product: text('product').notNull(),
  amountCents: integer('amount_cents').notNull(),
  email: text('email').notNull(),
  method: text('method').notNull().default('pix'),
  status: text('status').notNull(),
  providerId: text('provider_id').unique(),
  pixCode: text('pix_code'),
  createdAt: integer('created_at').notNull(),
  checkedAt: integer('checked_at').notNull().default(0),
}, table => [index('orders_ip_time').on(table.ipHash, table.createdAt)]);
