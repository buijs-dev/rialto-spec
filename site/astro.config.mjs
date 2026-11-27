import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { loadEnv } from 'vite';
import { existsSync } from 'node:fs';

// Where the site is served: https://rialto.buijs.dev/ (public/CNAME). SPEC_SITE and SPEC_BASE, from the environment
// or .env (written by CI, see .github/workflows/pages.yml), override it, for example for a preview elsewhere.
const env = { ...loadEnv('production', process.cwd(), 'SPEC_'), ...process.env };
const site = env.SPEC_SITE || 'https://rialto.buijs.dev';
const base = env.SPEC_BASE || '/';
const hasProfiles = existsSync(new URL('../spec/profiles', import.meta.url));

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
                { slug: 'index' },
                {
                    label: 'Specification',
                    items: [
                        { slug: 'spec/overview' },
                        { slug: 'spec/contract' },
                        { slug: 'spec/core' },
                        // One profile per slice: the group appears with the first one.
                        ...(hasProfiles
                            ? [{ label: 'Profiles', items: [{ autogenerate: { directory: 'spec/profiles' } }] }]
                            : []),
                    ],
                },
                {
                    label: 'Examples',
                    items: [{ slug: 'examples/contracts' }],
                },
                {
                    // The guides are ordered as docs/tooling.md lists them (scripts/sync.mjs).
                    label: 'Tooling and guides',
                    items: [
                        { slug: 'docs/tooling' },
                        { autogenerate: { directory: 'docs/guides' } },
                    ],
                },
                {
                    label: 'Project',
                    items: [{ slug: 'governance' }, { slug: 'contributing' }, { slug: 'changelog' }],
                },
            ],
        }),
    ],
});
