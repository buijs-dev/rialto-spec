import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { loadEnv } from 'vite';

// Where the site is served: https://rialto.buijs.dev/ (public/CNAME). SPEC_SITE and SPEC_BASE, from the environment
// or .env (written by CI, see .github/workflows/pages.yml), override it, for example for a preview elsewhere.
const env = { ...loadEnv('production', process.cwd(), 'SPEC_'), ...process.env };
const site = env.SPEC_SITE || 'https://rialto.buijs.dev';
const base = env.SPEC_BASE || '/';

export default defineConfig({
    site,
    base,
    trailingSlash: 'always',
    integrations: [
        starlight({
            title: 'Rialto',
            description: 'A contract-driven architecture for generated applications',
            social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/buijs-dev/rialto-spec' }],
            editLink: { baseUrl: 'https://github.com/buijs-dev/rialto-spec/edit/develop/' },
            sidebar: [
                {
                    label: 'Start',
                    items: [
                        { slug: 'index' },
                        { slug: 'docs/tooling' },
                    ],
                },
                {
                    label: 'Specification',
                    items: [
                        { slug: 'spec/overview' },
                        { slug: 'spec/contract' },
                        { slug: 'spec/core' },
                    ],
                },
                {
                    label: 'Examples',
                    items: [{ slug: 'examples/contracts' }],
                },
                {
                    label: 'Project',
                    items: [{ slug: 'governance' }, { slug: 'contributing' }, { slug: 'changelog' }],
                },
            ],
        }),
    ],
});
