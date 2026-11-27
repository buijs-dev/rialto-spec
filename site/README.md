# Site

The site at [rialto.buijs.dev](https://rialto.buijs.dev/), built with [Astro](https://astro.build/) and
[Starlight](https://starlight.astro.build/) from the Markdown of this repository. The specification is written once:
every page is a copy of a file elsewhere in the repository.

## Run it locally

Use the Node version in [`.nvmrc`](../.nvmrc).

```sh
cd site
npm ci                              # once
npm run dev                         # copies the Markdown, then serves http://localhost:4321/ with reload
npm run build && npm run preview    # the production build, as CI makes it
```

The dev server does not watch the files outside `site/`: after editing one, run `npm run sync` to copy them again.

`SITE_URL` and `SITE_BASE`, from the environment or `site/.env`, override where the site is served. Without them it is
`https://rialto.buijs.dev/`.

## Where the pages come from

[`scripts/sync.mjs`](scripts/sync.mjs) copies the sources into the site before every `dev` and `build`:

| Source | On the site |
|---|---|
| `README.md` | Home |
| `GOVERNANCE.md`, `CONTRIBUTING.md`, `CHANGELOG.md` | Governance, contributing, changelog |
| `docs/**/*.md` | Tooling and guides |
| `spec/**/*.md` | The specification |
| `examples/**/*.md` | Examples; a `README.md` is the index of its folder |
| `spec/*.schema.json` | Served at `/spec/<name>`, its `$id` |
| The Markdown above | `llms.txt` (index) and `llms-full.txt` (the specification in reading order) |

- The title of a page is the first `# ` heading of its file.
- A relative link to another copied Markdown file becomes a link to its page; a link to any other file points at the
  repository on GitHub (`develop`).
- The copies (`src/content/docs/`, `public/spec/`, `public/llms.txt`, `public/llms-full.txt`) are generated and ignored
  by git. Edit the source, never the copy.
- Only `astro.config.mjs`, `src/content.config.ts`, `public/CNAME` and `public/favicon.svg` belong to the site itself.

## A new page

The sidebar is in [`astro.config.mjs`](astro.config.mjs).

- A guide (`docs/guides/`) or a profile (`spec/profiles/`) appears by itself. Its place is the order in which
  `docs/tooling.md` or `spec/overview.md` links to it, so add the link there. The Profiles group appears with the first
  profile.
- Any other page is listed by hand: add its slug, such as `spec/generators` for `spec/generators.md`.

## Deployment

[`pages.yml`](../.github/workflows/pages.yml) builds the site and deploys it to GitHub Pages on every push to `develop`.
