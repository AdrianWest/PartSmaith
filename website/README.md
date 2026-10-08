# PartSmith website

Static project homepage for GitHub Pages. The site uses plain HTML and CSS;
there is no frontend compilation, JavaScript framework, package manager, or
external font. The deployment workflow copies the static files into an artifact.

## Files

- [index.html](../index.html): homepage at the repository root, including navigation and
  expandable questions.
- [website/installation.html](installation.html): installation guide published
  with the site, covering the current development candidate.
- [website/styles.css](styles.css): responsive layout, colors, and focus styles.
- [website/assets/PartSmith-Banner3.png](assets/PartSmith-Banner3.png): unchanged
  copy of [the owner's banner](../resources/PartSmith-Banner3.png).
- [.nojekyll](../.nojekyll): root marker for static files without a Jekyll build.

All local asset paths are relative, so the site works under the GitHub Pages
project path `/PartSmaith/`, at a domain root, or when opened locally.
Project links point to `https://github.com/AdrianWest/PartSmaith`; the installation
guide is part of the site and does not depend on a GitHub branch's documentation.
The homepage labels the project as in development and does not advertise an
unreleased candidate as a public production download.

## Preview

Double-click `index.html` at the repository root to open the site in a browser.
This does not require Python or a development environment.

For an optional HTTP preview, run the following **from the repository root**,
using this prepared checkout's existing Python environment:

```powershell
.venv/Scripts/python.exe -m http.server 8847 --bind 127.0.0.1
```

Then visit `http://127.0.0.1:8847`. Stop the preview server with Ctrl+C.

## Publish with GitHub Pages

The [website workflow](../.github/workflows/website.yml) assembles the root
`index.html`, `.nojekyll`, and the `website` guide/styles/assets into a dedicated
`_site` artifact.
It runs for homepage or website changes pushed to `main`, or can be run manually
from `main`. Application source and gate evidence are not included in the site.

1. In the repository's **Settings → Pages → Build and deployment**, set
   **Source** to **GitHub Actions**.
2. Commit and merge/push the root homepage, `.nojekyll`, `website` folder, and
   workflow to `main` when ready to publish. A matching push triggers deployment.
3. For a manual deployment, open **Actions → Deploy PartSmith website → Run
   workflow**, select `main`, and run it. Other branches are skipped by the job.
4. Confirm the workflow succeeds, then use **Settings → Pages → Visit site**.
   With no custom domain, the expected default URL is
   `https://adrianwest.github.io/PartSmaith/`.

GitHub requires the entry file at the top level of the **publishing source or
deployment artifact**. Here, `index.html` is at the repository root as requested
and is copied to `_site/index.html`. Choose **GitHub Actions** for this workflow;
its selected-file artifact contains the website rather than the entire checkout.

## Documentation verification

Checked on 2026-10-08 against GitHub's official Pages documentation, the current
workflow, homepage, and repository installation instructions. The root entry
file, relative assets, local guide link, workflow triggers/permissions, and
deployment artifact layout were verified locally. This check does not establish
that Pages is enabled or that a deployment has run on GitHub.

Creating these local files does not enable Pages, push changes, or publish a
website. See GitHub's [publishing source documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site),
[entry-file requirements](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site),
and [custom workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
