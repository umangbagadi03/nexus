from nexus.connectors.base import Connector, make_document
from nexus.connectors.markdown_cleaner import clean_markdown, split_front_matter
from nexus.connectors.repo_hosts import download_file, list_files


class MarkdownRepoConnector(Connector):
    """Docs, wikis and handbooks kept as markdown files in a GitHub or GitLab repository.

    Settings:
      provider      "github" or "gitlab"
      repo          for example "gitlab-com/content-sites/handbook"
      branch        for example "main"
      folders       folders to read, for example ["content/handbook/people-group"]
      strip_prefix  part of the file path that is not in the website URL, for example "content/"
      site_url      website the pages are published on, used for links. Optional.
      max_pages     stop after this many pages
    """

    type = "markdown_repo"
    label = "Markdown docs in a Git repository"

    def fetch(self, report_progress):
        provider = self.settings["provider"]
        repo = self.settings["repo"]
        branch = self.settings.get("branch", "main")
        max_pages = int(self.settings.get("max_pages", 300))

        paths = []
        for folder in self.settings["folders"]:
            for path in list_files(provider, repo, branch, folder):
                if path.endswith(".md") or path.endswith(".mdx"):
                    paths.append(path)

        paths = paths[:max_pages]
        report_progress("Found " + str(len(paths)) + " pages")

        documents = []
        for number, path in enumerate(paths, start=1):
            raw_text = download_file(provider, repo, branch, path)
            document = self.build_document(path, raw_text)
            if document is not None:
                documents.append(document)

            if number % 10 == 0:
                report_progress("Downloaded " + str(number) + " of " + str(len(paths)) + " pages")

        return documents

    def build_document(self, path, raw_text):
        title, body = split_front_matter(raw_text)
        text = clean_markdown(body)

        # Pages that are only a list of links, or a redirect, have nothing to search
        if len(text) < 200:
            return None

        page_path = self.page_path(path)
        if not title:
            title = page_path.split("/")[-1].replace("-", " ").capitalize()

        return make_document(
            document_id=page_path,
            kind="docs",
            title=title,
            text="Title: " + title + "\n\n" + text,
            url=self.page_url(path, page_path),
        )

    def page_path(self, path):
        # content/handbook/people-group/_index.md -> handbook/people-group
        strip_prefix = self.settings.get("strip_prefix", "")
        if strip_prefix and path.startswith(strip_prefix):
            path = path[len(strip_prefix):]

        path = path.replace(".mdx", "").replace(".md", "")
        if path.endswith("/_index") or path.endswith("/index"):
            path = path.rsplit("/", 1)[0]
        return path.strip("/")

    def page_url(self, path, page_path):
        site_url = self.settings.get("site_url", "")
        if site_url:
            return site_url.rstrip("/") + "/" + page_path

        # No website: link to the file in the repository
        repo = self.settings["repo"]
        branch = self.settings.get("branch", "main")
        if self.settings["provider"] == "github":
            return "https://github.com/" + repo + "/blob/" + branch + "/" + path
        return "https://gitlab.com/" + repo + "/-/blob/" + branch + "/" + path
