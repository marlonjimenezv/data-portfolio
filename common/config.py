"""Portfolio-wide settings. Change GITHUB_USER / REPO here if the repo name changes."""

AUTHOR = "Marlon Jiménez Valencia"
GITHUB_USER = "marlonjimenezv"
REPO = "data-portfolio"
BRANCH = "main"

REPO_URL = f"https://github.com/{GITHUB_USER}/{REPO}"
PAGES_URL = f"https://{GITHUB_USER}.github.io/{REPO}"


def folder_url(folder: str) -> str:
    return f"{REPO_URL}/tree/{BRANCH}/{folder}"


def file_url(path: str) -> str:
    return f"{REPO_URL}/blob/{BRANCH}/{path}"
