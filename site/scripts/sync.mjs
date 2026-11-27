// Copies the Markdown of the repository into the site, so the specification is written once.
// Every page gets its title from the first heading, and links between pages are rewritten to
// site paths; links to other files (examples, schema) point at the repository on GitHub.
// The copy in src/content/docs and public/ is generated and not committed.
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, posix, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';

const siteDir = join(dirname(fileURLToPath(import.meta.url)), '..');
const root = join(siteDir, '..');
const out = join(siteDir, 'src', 'content', 'docs');
const env = { ...loadEnv('production', siteDir, 'SPEC_'), ...process.env };
const base = (env.SPEC_BASE || '/').replace(/\/$/, '');
const repository = 'https://github.com/buijs-dev/rialto-spec/blob/develop';

const top = ['README.md', 'GOVERNANCE.md', 'CONTRIBUTING.md', 'CHANGELOG.md'];
const folders = ['docs', 'spec', 'examples'];

const markdown = [];
const walk = (directory) => {
    for (const name of readdirSync(directory)) {
        const path = join(directory, name);
        if (statSync(path).isDirectory()) walk(path);
        else if (name.endsWith('.md')) markdown.push(relative(root, path).split(sep).join('/'));
    }
};
top.forEach((file) => markdown.push(file));
// The specification is built in slices: a folder of a later slice may not be there yet.
folders.filter((folder) => existsSync(join(root, folder))).forEach((folder) => walk(join(root, folder)));

// repository path -> page path, without base: README.md is the index of its directory
const page = (file) => {
    const noExt = file.replace(/\.md$/, '');
    if (noExt === 'README') return '';
    if (noExt.endsWith('/README')) return noExt.slice(0, -'/README'.length) + '/';
    return noExt.toLowerCase() === noExt ? noExt + '/' : noExt.toLowerCase() + '/';
};
const slug = (file) => {
    const p = page(file);
    return p === '' ? 'index' : p.endsWith('/') ? (file.endsWith('README.md') ? p + 'index' : p.slice(0, -1)) : p;
};
const known = new Set(markdown);

const rewrite = (file, text) => {
    let fenced = false;
    return text
        .split('\n')
        .map((line) => {
            if (/^\s*(```|~~~)/.test(line)) fenced = !fenced;
            if (fenced) return line;
            return line.replace(/\]\(([^)\s]+)\)/g, (whole, target) => {
                if (/^([a-z][a-z0-9+.-]*:|#|\/)/i.test(target)) return whole;
                const [path, anchor] = target.split('#');
                const resolved = posix.normalize(posix.join(posix.dirname(file), path));
                const suffix = anchor ? '#' + anchor : '';
                if (known.has(resolved)) return `](${base}/${page(resolved)}${suffix})`;
                if (existsSync(join(root, resolved))) {
                    const isDirectory = statSync(join(root, resolved)).isDirectory();
                    return `](${repository.replace('/blob/', isDirectory ? '/tree/' : '/blob/')}/${resolved}${suffix})`;
                }
                return whole;
            });
        })
        .join('\n');
};

// A folder the sidebar generates (astro.config.mjs) is ordered as the document that lists it links to its pages.
const listedBy = { 'docs/guides/': 'docs/tooling.md', 'spec/profiles/': 'spec/overview.md' };
const sidebarOrder = (file) => {
    const folder = Object.keys(listedBy).find((prefix) => file.startsWith(prefix));
    if (!folder || !known.has(listedBy[folder])) return undefined;
    const lister = listedBy[folder];
    const targets = [...readFileSync(join(root, lister), 'utf8').matchAll(/\]\(([^)#\s]+)/g)]
        .map((match) => posix.normalize(posix.join(posix.dirname(lister), match[1])));
    const position = targets.indexOf(file);
    return position === -1 ? undefined : position;
};

rmSync(out, { recursive: true, force: true });
rmSync(join(siteDir, 'public', 'spec'), { recursive: true, force: true });

for (const file of markdown) {
    let text = readFileSync(join(root, file), 'utf8');
    const heading = text.match(/^# (.+)$/m);
    const title = heading ? heading[1].trim() : file;
    if (heading) text = text.replace(/^# .+\n/m, '');
    const sidebarLabel = file === 'README.md' ? 'Introduction' : title;
    const order = sidebarOrder(file);
    const frontmatter = `---\ntitle: ${JSON.stringify(title)}\nsidebar:\n  label: ${JSON.stringify(sidebarLabel)}\n`
        + (order === undefined ? '' : `  order: ${order}\n`) + '---\n\n';
    const target = join(out, slug(file) + '.md');
    mkdirSync(dirname(target), { recursive: true });
    writeFileSync(target, frontmatter + rewrite(file, text));
}

// The schemas are served at stable paths, their $id: <site>/spec/contract-1.0.0.schema.json.
mkdirSync(join(siteDir, 'public', 'spec'), { recursive: true });
for (const schema of readdirSync(join(root, 'spec')).filter((name) => name.endsWith('.schema.json'))) {
    cpSync(join(root, 'spec', schema), join(siteDir, 'public', 'spec', schema));
}

// For AI tools (https://llmstxt.org): an index, and the whole specification in reading order as one file.
const siteUrl = (env.SPEC_SITE || 'https://rialto.buijs.dev') + base;
const order = ['README.md', 'spec/overview.md', 'spec/contract.md', 'spec/core.md',
    ...markdown.filter((file) => file.startsWith('spec/profiles/')).sort(),
    'spec/generators.md', 'examples/shipment/README.md', 'examples/contracts/README.md'].filter((file) => known.has(file));
const titleOf = (file) => (readFileSync(join(root, file), 'utf8').match(/^# (.+)$/m) || [, file])[1].trim();
const index = ['# Rialto', '', '> A contract-driven architecture for generated applications: one contract, read by generators',
    '> in any language, binds OpenAPI, AsyncAPI and SQL to one domain.', '',
    `The whole specification in one file: ${siteUrl}/llms-full.txt`, `JSON Schema: ${siteUrl}/spec/contract-1.0.0.schema.json`, '',
    '## Specification', '', ...order.map((file) => `- [${titleOf(file)}](${siteUrl}/${page(file)})`), ''].join('\n');
writeFileSync(join(siteDir, 'public', 'llms.txt'), index);
writeFileSync(join(siteDir, 'public', 'llms-full.txt'),
    order.map((file) => `<!-- ${file} -->\n\n${readFileSync(join(root, file), 'utf8')}`).join('\n\n'));

console.log(`synced ${markdown.length} pages into ${relative(siteDir, out)}`);
