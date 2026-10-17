CREATE TABLE `orders` (
	`id` text PRIMARY KEY NOT NULL,
	`token_hash` text NOT NULL,
	`ip_hash` text NOT NULL,
	`product` text NOT NULL,
	`amount_cents` integer NOT NULL,
	`email` text NOT NULL,
	`status` text NOT NULL,
	`provider_id` text,
	`pix_code` text,
	`created_at` integer NOT NULL,
	`checked_at` integer DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `orders_provider_id_unique` ON `orders` (`provider_id`);--> statement-breakpoint
CREATE INDEX `orders_ip_time` ON `orders` (`ip_hash`,`created_at`);