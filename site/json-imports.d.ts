// Overrides Next.js/TypeScript's default behavior of inferring the exact
// literal type of every JSON file imported via `resolveJsonModule`. That's
// harmless for small files, but for our scraped data.json files (which grow
// to hundreds of entries with long text fields), computing that literal type
// is memory-intensive enough to have silently killed the Vercel build during
// type-checking. Declaring JSON imports as `any` here skips that inference
// entirely — we cast to the real type explicitly right after import in
// lib/data.ts anyway, so no type safety is actually lost in practice.
declare module "*.json" {
  const value: any;
  export default value;
}
