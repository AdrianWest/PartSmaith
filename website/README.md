# PartSmith website

Static project homepage for GitHub Pages. The site uses plain HTML and CSS;
there is no JavaScript framework, build step, package manager, or external font.

## Files

- `/index.html`: homepage at the repository root, including navigation and
  expandable questions.
- `/website/styles.css`: responsive layout, colors, and keyboard focus styles.
- `/website/assets/PartSmith-Banner3.png`: unchanged copy of the owner's banner
  from `resources/PartSmith-Banner3.png`.
- `/.nojekyll`: root marker for serving static files without a Jekyll build.

All local asset paths are relative, so the site works under the GitHub Pages
project path `/PartSmaith/`, at a domain root, or when opened locally.
Repository links point to `https://github.com/AdrianWest/PartSmaith`.
The homepage labels the project as in development and does not advertise an
unreleased candidate as a public production download.

## Preview

Open `index.html` at the repository root in a browser, or serve the repository:

```powershell
.venv/Scripts/python.exe -m http.server 8847 --bind 127.0.0.1
```

Then visit `http://127.0.0.1:8847`. Stop the preview server with Ctrl+C.

## Publish with GitHub Pages

The workflow in `.github/workflows/website.yml` assembles the root `index.html`,
`.nojekyll`, and `website` styles/assets into a dedicated `_site` artifact.
It runs for homepage or website changes pushed to `main`, or can be run manually
from `main`. Application source and gate evidence are not included in the site.

1. Commit and push the website and workflow to `main` when ready to publish.
2. In the repository's **Settings → Pages → Build and deployment**, set
   **Source** to **GitHub Actions**.
3. Run **Deploy PartSmith website** from the **Actions** tab if necessary.
4. After deployment, the expected default URL is
   `https://adrianwest.github.io/PartSmaith/`.

Creating these local files does not enable Pages, push changes, or publish a
website. See GitHub's [publishing source documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
and [custom workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
