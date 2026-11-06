import * as api from "../api.js";
import { clear, el } from "../dom.js";
import { timeAgo } from "../format.js";
import { icon } from "../icons.js";
import { reloadWorkspace } from "../main.js";
import { state } from "../state.js";

const TYPE_LABELS = {
  files: "Uploaded files",
  markdown_repo: "Markdown docs in a Git repository",
  github_issues: "GitHub issues and pull requests",
  pushed: "Pushed through the API",
};

// Which kind color each source type uses
const TYPE_KINDS = {
  files: "file",
  markdown_repo: "docs",
  github_issues: "issue",
  pushed: "note",
};

let tableHolder = null;
let pollTimer = null;


export function renderSourcesPage(container) {
  container.appendChild(el("h2", "section-title", "Connected sources"));
  container.appendChild(el("p", "section-intro",
    "Everything Nexus can search in this workspace. Each sync indexes only new and changed documents, " +
    "removes deleted ones, and updates the links between documents."));

  tableHolder = el("div");
  container.appendChild(tableHolder);
  renderSourceTable();

  container.appendChild(buildAddSource());
}


function renderSourceTable() {
  clear(tableHolder);
  const sources = state.workspace.sources;

  if (sources.length === 0) {
    tableHolder.appendChild(el("p", "empty", "No sources yet. Add one below."));
    return;
  }

  const table = el("ul", "source-table");
  let anySyncing = false;

  for (const source of sources) {
    if (source.status === "syncing" || source.status === "queued") {
      anySyncing = true;
    }
    table.appendChild(buildSourceRow(source));
  }

  tableHolder.appendChild(table);

  // While something syncs, refresh every two seconds to show its progress
  clearTimeout(pollTimer);
  if (anySyncing) {
    pollTimer = setTimeout(refreshWhileSyncing, 2000);
  }
}


async function refreshWhileSyncing() {
  if (!tableHolder || !document.body.contains(tableHolder)) {
    return;
  }
  await reloadWorkspace();
  renderSourceTable();
}


function sourceDetail(source) {
  const settings = source.settings;
  if (source.type === "markdown_repo") {
    if (settings.folders.length === 1) {
      return settings.repo + ", " + settings.folders[0];
    }
    return settings.repo + ", " + settings.folders.length + " folders";
  }
  if (source.type === "github_issues") {
    return settings.repo + ", latest " + settings.max_items;
  }
  return TYPE_LABELS[source.type];
}


function buildSourceRow(source) {
  const row = el("li", "source-row kind-" + TYPE_KINDS[source.type]);

  const info = el("div", "source-info");

  const name = el("div", "source-name");
  name.appendChild(el("span", "kind-dot"));
  name.appendChild(el("span", "", source.name));
  info.appendChild(name);

  const detail = el("p", "source-detail", sourceDetail(source));
  if (source.settings.folders) {
    detail.title = source.settings.folders.join("\n");
  }
  info.appendChild(detail);

  const facts = el("div", "source-facts");
  const documents = el("span", "source-documents");
  documents.appendChild(el("strong", "", source.documents));
  documents.appendChild(document.createTextNode(" documents"));
  facts.appendChild(documents);
  facts.appendChild(buildStatus(source));
  info.appendChild(facts);

  row.appendChild(info);
  row.appendChild(buildActions(source));
  return row;
}


function buildStatus(source) {
  const status = el("div", "source-status status-" + source.status);
  const line = el("span", "status-line");

  if (source.status === "queued") {
    line.appendChild(el("span", "spinner"));
    line.appendChild(document.createTextNode("Waiting"));
  } else if (source.status === "syncing") {
    line.appendChild(el("span", "spinner"));
    line.appendChild(document.createTextNode("Syncing"));
  } else if (source.status === "ready") {
    line.appendChild(document.createTextNode("Synced " + timeAgo(source.last_synced)));
  } else if (source.status === "failed") {
    line.appendChild(document.createTextNode("Sync failed"));
  } else {
    line.appendChild(document.createTextNode("Not synced yet"));
  }

  status.appendChild(line);
  if (source.message) {
    status.appendChild(el("span", "status-message", source.message));
  }
  return status;
}


function buildActions(source) {
  const actions = el("div", "source-actions");
  const busy = source.status === "syncing" || source.status === "queued";

  const syncButton = el("button", "button quiet");
  syncButton.type = "button";
  syncButton.appendChild(icon("sync"));
  syncButton.appendChild(document.createTextNode("Sync"));
  syncButton.disabled = busy;
  syncButton.addEventListener("click", async function () {
    await api.syncSource(state.workspace.id, source.id);
    await reloadWorkspace();
    renderSourceTable();
  });
  actions.appendChild(syncButton);

  const removeButton = el("button", "button quiet danger");
  removeButton.type = "button";
  removeButton.appendChild(icon("remove"));
  removeButton.appendChild(document.createTextNode("Remove"));
  removeButton.disabled = busy;
  removeButton.addEventListener("click", async function () {
    const sure = window.confirm("Remove " + source.name + "? Its documents will no longer be searchable.");
    if (!sure) {
      return;
    }
    await api.removeSource(state.workspace.id, source.id);
    await reloadWorkspace();
    renderSourceTable();
  });
  actions.appendChild(removeButton);

  return actions;
}


/* Adding a source */

const ADD_OPTIONS = [
  ["upload", "upload", "Upload files"],
  ["repo", "repo", "Docs from a Git repository"],
  ["issues", "issues", "GitHub issues"],
  ["api", "api", "Push API"],
];

function buildAddSource() {
  const box = el("section", "add-source");
  box.appendChild(el("h2", "section-title", "Add a source"));

  const tabs = el("div", "add-tabs");
  const formHolder = el("div");

  for (const option of ADD_OPTIONS) {
    const button = el("button");
    button.type = "button";
    button.appendChild(icon(option[1]));
    button.appendChild(document.createTextNode(option[2]));
    button.addEventListener("click", function () {
      for (const other of tabs.children) {
        other.classList.remove("active");
      }
      button.classList.add("active");
      clear(formHolder);
      formHolder.appendChild(buildAddForm(option[0]));
    });
    tabs.appendChild(button);
  }

  box.appendChild(tabs);
  box.appendChild(formHolder);

  tabs.firstChild.classList.add("active");
  formHolder.appendChild(buildAddForm("upload"));
  return box;
}


function buildAddForm(kind) {
  if (kind === "upload") {
    return buildUploadForm();
  }
  if (kind === "repo") {
    return buildRepoForm();
  }
  if (kind === "issues") {
    return buildIssuesForm();
  }
  return buildApiHelp();
}


function field(labelText, input, hint) {
  const label = el("label", "field");
  label.appendChild(document.createTextNode(labelText));
  label.appendChild(input);
  if (hint) {
    label.appendChild(el("small", "", hint));
  }
  return label;
}


function textInput(name, placeholder, value) {
  const input = el("input");
  input.name = name;
  input.placeholder = placeholder || "";
  input.value = value || "";
  return input;
}


function formActions(buttonText) {
  const actions = el("div", "add-form-actions");
  const button = el("button", "button", buttonText);
  button.type = "submit";
  const message = el("span", "form-message");
  actions.appendChild(button);
  actions.appendChild(message);
  return actions;
}


// Shared submit handling: show progress, call the API, refresh the source list
function handleSubmit(form, sendRequest) {
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    const message = form.querySelector(".form-message");

    button.disabled = true;
    message.className = "form-message";
    message.textContent = "Adding";

    try {
      await sendRequest();
      message.textContent = "Added. Syncing now, you can follow it above.";
      form.reset();
      await reloadWorkspace();
      renderSourceTable();
    } catch (error) {
      message.className = "form-message error";
      message.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}


function buildUploadForm() {
  const form = el("form", "add-form");
  let chosenFiles = [];

  const zone = el("label", "drop-zone");
  zone.appendChild(icon("upload"));
  zone.appendChild(el("strong", "", "Drop files here, or click to choose"));
  zone.appendChild(el("span", "", "PDF, Word, Markdown or text. Policies, runbooks, design docs, meeting notes."));

  const input = el("input");
  input.type = "file";
  input.multiple = true;
  input.accept = ".pdf,.docx,.md,.mdx,.txt";
  zone.appendChild(input);
  form.appendChild(zone);

  const fileList = el("ul", "chosen-files");
  form.appendChild(fileList);

  function showChosen(files) {
    chosenFiles = Array.from(files);
    clear(fileList);
    for (const file of chosenFiles) {
      fileList.appendChild(el("li", "", file.name));
    }
  }

  input.addEventListener("change", function () {
    showChosen(input.files);
  });
  zone.addEventListener("dragover", function (event) {
    event.preventDefault();
    zone.classList.add("dragging");
  });
  zone.addEventListener("dragleave", function () {
    zone.classList.remove("dragging");
  });
  zone.addEventListener("drop", function (event) {
    event.preventDefault();
    zone.classList.remove("dragging");
    showChosen(event.dataTransfer.files);
  });

  const nameInput = textInput("source_name", "", "Uploaded files");
  form.appendChild(field("Add to source", nameInput, "Files with the same source name are grouped together."));
  form.appendChild(formActions("Upload and index"));

  handleSubmit(form, function () {
    if (chosenFiles.length === 0) {
      throw new Error("Choose at least one file.");
    }
    return api.uploadFiles(state.workspace.id, chosenFiles, nameInput.value.trim() || "Uploaded files");
  });

  return form;
}


function buildRepoForm() {
  const form = el("form", "add-form");

  const provider = el("select");
  provider.name = "provider";
  const hosts = [["github", "GitHub"], ["gitlab", "GitLab"]];
  for (const host of hosts) {
    const option = el("option", "", host[1]);
    option.value = host[0];
    provider.appendChild(option);
  }

  const repo = textInput("repo", "owner/repository");
  const branch = textInput("branch", "main", "main");
  const folder = textInput("folder", "docs");
  const siteUrl = textInput("site_url", "https://docs.example.com");

  form.appendChild(field("Host", provider));
  form.appendChild(field("Repository", repo));
  form.appendChild(field("Branch", branch));
  form.appendChild(field("Folder with markdown files", folder));
  const siteField = field("Website the docs are published on", siteUrl, "Optional. Used to link answers to the real pages.");
  siteField.classList.add("wide");
  form.appendChild(siteField);
  form.appendChild(formActions("Add and sync"));

  handleSubmit(form, function () {
    return api.addMarkdownRepo(state.workspace.id, {
      provider: provider.value,
      repo: repo.value.trim(),
      branch: branch.value.trim(),
      folder: folder.value.trim(),
      site_url: siteUrl.value.trim(),
    });
  });

  return form;
}


function buildIssuesForm() {
  const form = el("form", "add-form");

  const repo = textInput("repo", "owner/repository");
  const maxItems = textInput("max_items", "", "200");
  maxItems.type = "number";
  maxItems.min = "10";
  maxItems.max = "2000";

  form.appendChild(field("Repository", repo));
  form.appendChild(field("How many to fetch", maxItems, "The most recently updated issues and pull requests."));
  form.appendChild(formActions("Add and sync"));

  handleSubmit(form, function () {
    return api.addGitHubIssues(state.workspace.id, {
      repo: repo.value.trim(),
      max_items: Number(maxItems.value) || 200,
    });
  });

  return form;
}


function buildApiHelp() {
  const box = el("div");
  box.appendChild(el("p", "api-intro",
    "Any system can send documents to Nexus: a wiki, a ticketing tool, a nightly export or a script. " +
    "Sending a document with the same id again updates it. Only the changed documents are re-indexed."));

  const example =
    "curl -X POST " + window.location.origin + "/api/workspaces/" + state.workspace.id + "/documents \\\n" +
    "  -H \"Content-Type: application/json\" \\\n" +
    "  -d '{\n" +
    "    \"source_name\": \"Confluence export\",\n" +
    "    \"documents\": [\n" +
    "      {\n" +
    "        \"id\": \"onboarding-guide\",\n" +
    "        \"title\": \"Engineering onboarding guide\",\n" +
    "        \"text\": \"## First week\\nSet up your laptop...\",\n" +
    "        \"url\": \"https://wiki.example.com/onboarding\"\n" +
    "      }\n" +
    "    ]\n" +
    "  }'";

  box.appendChild(el("pre", "code-block", example));
  box.appendChild(el("p", "form-message",
    "For a source that should be pulled on a schedule instead, write a connector: subclass Connector in nexus/connectors/base.py."));
  return box;
}
