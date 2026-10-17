import { build } from 'esbuild';
import { pathToFileURL } from 'node:url';
globalThis.mockEnv={};
await build({entryPoints:['tests/payments.test.ts'],outfile:'/tmp/skillverse-payment-tests.mjs',bundle:true,platform:'node',format:'esm',target:'node24',packages:'external',plugins:[{name:'cloudflare-test-env',setup(build){build.onResolve({filter:/^cloudflare:workers$/},()=>({path:'cloudflare:workers',namespace:'mock'}));build.onLoad({filter:/.*/,namespace:'mock'},()=>({contents:'export const env = globalThis.mockEnv;',loader:'js'}));}}]});
await import(pathToFileURL('/tmp/skillverse-payment-tests.mjs').href);
