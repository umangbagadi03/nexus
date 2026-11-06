import * as api from "../api.js";
import { clear, el } from "../dom.js";
import { icon } from "../icons.js";
import { openWorkspace, reloadWorkspaceList, renderSidebar } from "../main.js";
import { state } from "../state.js";

// Each connector type, with the icon and color it uses everywhere in the app
export const CONNECTOR_INFO = {
  files: { icon: "file", kind: "file", label: "Uploaded files" },
  markdown_repo: { icon: "repo", kind: "docs", label: "Docs from a Git repository" },
  github_issues: { icon: "issues", kind: "issue", label: "GitHub issues and pull requests" },
  pushed: { icon: "api", kind: "note", label: "Push API" },
};

const STEPS = [
  [
    "Connect your sources",
    "Upload files, point Nexus at docs in a GitHub or GitLab repository, pull GitHub issues, " +
    "or send documents from any other system through the push API.",
  ],
  [
    "Nexus indexes and links them",
    "Every section is searchable by meaning and by exact keywords. Links between documents, like an issue " +
    "and the pull request that fixed it, or a policy and the pages it refers to, become a graph.",
  ],
  [
    "Ask in plain language",
    "An agent searches, follows the links, checks whether it found enough, and answers with citations " +
    "you can click through to the original page.",
  ],
];

let listHolder = null;


export function renderHomePage(container) {
  document.title = "Nexus";

  const hero = el("section", "home-hero");
  hero.appendChild(el("h1", "", "Ask questions across your company's knowledge"));
  hero.appendChild(el("p", "",
    "Nexus connects to the places where your team writes things down and answers questions from them, " +
    "showing exactly which documents each answer came from."));
  container.appendChild(hero);

  const steps = el("ol", "steps");
  for (const step of STEPS) {
    const item = el("li");
    item.appendChild(el("strong", "", step[0]));
    item.appendChild(el("span", "", step[1]));
    steps.appendChild(item);
  }
  container.appendChild(steps);

  const section = el("section", "home-workspaces");
  const heading = el("div", "home-workspaces-heading");
  heading.appendChild(el("h2", "section-title", "Workspaces"));

  const newButton = el("button", "button");
  newButton.type = "button";
  newButton.appendChild(icon("plus"));
  newButton.appendChild(document.createTextNode("New workspace"));
  heading.appendChild(newButton);
  section.appendChild(heading);

  section.appendChild(el("p", "section-intro",
    "Each workspace has its own sources, index and evaluation set, and never sees another workspace's documents. " +
    "The two below are samples built from public data: GitLab's company handbook, and the LangGraph project's docs, issues and pull requests."));

  const form = buildNewWorkspaceForm();
  form.hidden = true;
  section.appendChild(form);
  newButton.addEventListener("click", function () {
    form.hidden = false;
    form.querySelector("input").focus();
  });

  listHolder = el("div");
  section.appendChild(listHolder);
  renderWorkspaceList();

  container.appendChild(section);
}


async function renderWorkspaceList() {
  const workspaces = await reloadWorkspaceList();
  clear(listHolder);

  if (workspaces.length === 0) {
    listHolder.appendChild(el("p", "empty", "No workspaces yet. Create one, or run `python main.py setup-demo` for the samples."));
    return;
  }

  const list = el("ul", "workspace-list");
  for (const workspace of workspaces) {
    list.appendChild(buildWorkspaceRow(workspace));
  }
  listHolder.appendChild(list);
}


function buildWorkspaceRow(workspace) {
  const row = el("li", "workspace-row");

  const info = el("div", "workspace-info");
  const name = el("button", "workspace-name", workspace.name);
  name.type = "button";
  name.addEventListener("click", function () {
    openWorkspace(workspace.id, "ask");
  });
  info.appendChild(name);

  if (workspace.description) {
    info.appendChild(el("p", "workspace-description", workspace.description));
  }

  const connectors = el("ul", "connector-list");
  if (workspace.sources.length === 0) {
    connectors.appendChild(el("li", "empty", "No sources connected yet"));
  }
  for (const source of workspace.sources) {
    const connector = CONNECTOR_INFO[source.type];
    const item = el("li", "connector kind-" + connector.kind);
    item.title = connector.label;
    item.appendChild(icon(connector.icon));
    item.appendChild(el("span", "", source.name));
    item.appendChild(el("strong", "", source.documents));
    connectors.appendChild(item);
  }
  info.appendChild(connectors);
  row.appendChild(info);

  const actions = el("div", "workspace-actions");
  const askButton = el("button", "button", "Ask");
  askButton.type = "button";
  askButton.addEventListener("click", function () {
    openWorkspace(workspace.id, "ask");
  });
  const sourcesButton = el("button", "button quiet", "Manage sources");
  sourcesButton.type = "button";
  sourcesButton.addEventListener("click", function () {
    openWorkspace(workspace.id, "sources");
  });
  actions.appendChild(askButton);
  actions.appendChild(sourcesButton);

  const deleteButton = el("button", "button quiet danger");
  deleteButton.type = "button";
  deleteButton.title = "Delete " + workspace.name;
  deleteButton.setAttribute("aria-label", "Delete " + workspace.name);
  deleteButton.appendChild(icon("remove"));
  deleteButton.addEventListener("click", async function () {
    const sure = window.confirm("Delete " + workspace.name + "? Its index, documents and uploaded files are removed.");
    if (!sure) {
      return;
    }
    try {
      await api.deleteWorkspace(workspace.id);
    } catch (error) {
      window.alert(error.message);
      return;
    }
    await renderWorkspaceList();

    // If the open workspace was deleted, switch the sidebar to the first one left
    if (state.workspace && state.workspace.id === workspace.id) {
      state.workspace = null;
      if (state.workspaces.length > 0) {
        state.workspace = await api.getWorkspace(state.workspaces[0].id);
        renderSidebar();
      }
    }
  });
  actions.appendChild(deleteButton);

  row.appendChild(actions);

  return row;
}


function buildNewWorkspaceForm() {
  const form = el("form", "new-workspace");

  const nameLabel = el("label", "field");
  nameLabel.appendChild(document.createTextNode("Name"));
  const nameInput = el("input");
  nameInput.placeholder = "For example: Acme Engineering";
  nameInput.required = true;
  nameLabel.appendChild(nameInput);
  form.appendChild(nameLabel);

  const descriptionLabel = el("label", "field");
  descriptionLabel.appendChild(document.createTextNode("What is in it"));
  const descriptionInput = el("input");
  descriptionInput.placeholder = "For example: runbooks, policies and design docs of the platform team";
  descriptionLabel.appendChild(descriptionInput);
  form.appendChild(descriptionLabel);

  const actions = el("div", "new-workspace-actions");
  const createButton = el("button", "button", "Create and add sources");
  createButton.type = "submit";
  const cancelButton = el("button", "button quiet", "Cancel");
  cancelButton.type = "button";
  const message = el("span", "form-message error");
  actions.appendChild(createButton);
  actions.appendChild(cancelButton);
  actions.appendChild(message);
  form.appendChild(actions);

  cancelButton.addEventListener("click", function () {
    form.reset();
    message.textContent = "";
    form.hidden = true;
  });

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    createButton.disabled = true;
    message.textContent = "";

    try {
      const workspace = await api.createWorkspace(nameInput.value.trim(), descriptionInput.value.trim());
      await reloadWorkspaceList();
      openWorkspace(workspace.id, "sources");
    } catch (error) {
      message.textContent = error.message;
    } finally {
      createButton.disabled = false;
    }
  });

  return form;
}
