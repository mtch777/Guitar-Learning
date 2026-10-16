# Songsterr downloader integration

Reserved for integration of https://github.com/Metaphysics0/songsterr-downloader (MIT-licensed).

The upstream project is a SvelteKit/TypeScript web app that fetches Songsterr revision JSON, converts it with `@coderline/alphatab`, and exports GP7 files. The upstream source has **not** been copied or vendored here. The API smoke tests live in the sibling `songsterr_api/` directory.

Next integration step: select whether to embed the upstream converter or invoke a separately hosted service; keep source attribution and license, and test against representative multi-track scores.
