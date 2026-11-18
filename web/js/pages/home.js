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
    "and the pull request linked to it, or a policy and the pages it refers to, become a graph.",
  ],
  [
    "Ask in plain language",
    "An agent searches, follows the links, checks whether it found enough, and answers with citations " +
    "you can click through to the original page.",
  ],
];

// A real answer from the LangGraph eval set (question q13), shown on the home page
// so people see what Nexus produces before they open a workspace
const SAMPLE_ANSWER = {
  workspace: "LangGraph",
  question: "With ToolNode, messages added through Command.update end up between parallel tool results " +
    "and later requests fail. Is this fixed?",
  // Each part is plain text, bold text, or a citation number
  answer: [
    ["text", "No, this is not fixed. While a pull request was created to address this issue, "],
    ["bold", "Pull Request #9560"],
    ["text", " was closed without being merged "],
    ["cite", "2"],
    ["text", ". Consequently, the bug described in "],
    ["bold", "Issue #9556"],
    ["text", " remains open "],
    ["cite", "1"],
    ["text", "."],
  ],
  sources: [
    ["1", "issue", "ToolNode: messages added via Command.update end up between parallel tool results, so every later request fails", "Issue #9556, open"],
    ["2", "pr", "fix(prebuilt): keep parallel tool results contiguous", "Pull request #9560, closed without merging"],
  ],
};

let listHolder = null;


export function renderHomePage(container) {
  document.title = "Nexus";

  const form = buildNewWorkspaceForm();
  form.hidden = true;

  function showNewWorkspaceForm() {
    form.hidden = false;
    form.scrollIntoView({ block: "center" });
    form.querySelector("input").focus();
  }

  container.appendChild(buildHero(showNewWorkspaceForm));
  container.appendChild(buildSteps());

  const section = el("section", "home-workspaces");
  const heading = el("div", "home-workspaces-heading");
  heading.appendChild(el("h2", "section-title", "Workspaces"));

  const newButton = el("button", "button quiet writes");
  newButton.type = "button";
  newButton.appendChild(icon("plus"));
  newButton.appendChild(document.createTextNode("New workspace"));
  newButton.addEventListener("click", showNewWorkspaceForm);
  heading.appendChild(newButton);
  section.appendChild(heading);

  section.appendChild(el("p", "section-intro",
    "Each workspace has its own sources, index and evaluation set, and never sees another workspace's documents. " +
    "The samples use public data: GitLab's handbook, the LangGraph project, and one generated PDF."));

  section.appendChild(form);

  listHolder = el("div");
  section.appendChild(listHolder);
  renderWorkspaceList();

  container.appendChild(section);
}


function buildHero(showNewWorkspaceForm) {
  const hero = el("section", "home-hero");

  const text = el("div", "home-hero-text");
  text.appendChild(el("h1", "", "Ask your company's documents and see where every answer comes from"));
  text.appendChild(el("p", "",
    "Connect handbooks, PDFs, docs in Git and GitHub issues. Nexus searches them, follows the links " +
    "between them, and answers with citations you can open."));

  const actions = el("div", "home-hero-actions");
  const askButton = el("button", "button", "Ask a question");
  askButton.type = "button";
  askButton.addEventListener("click", function () {
    let workspaceId = null;
    if (state.workspace) {
      workspaceId = state.workspace.id;
    } else if (state.workspaces.length > 0) {
      workspaceId = state.workspaces[0].id;
    }

    if (workspaceId) {
      openWorkspace(workspaceId, "ask");
    } else {
      showNewWorkspaceForm();
    }
  });
  const createButton = el("button", "button quiet writes", "Create a workspace");
  createButton.type = "button";
  createButton.addEventListener("click", showNewWorkspaceForm);
  actions.appendChild(askButton);
  actions.appendChild(createButton);
  text.appendChild(actions);

  hero.appendChild(text);
  hero.appendChild(buildAnswerPreview());
  return hero;
}


// The sample answer, drawn the same way the Ask page draws a real one
function buildAnswerPreview() {
  const preview = el("figure", "preview");

  const top = el("div", "preview-top");
  top.appendChild(el("span", "", SAMPLE_ANSWER.workspace));
  top.appendChild(el("span", "", "Agentic pipeline"));
  preview.appendChild(top);

  preview.appendChild(el("p", "preview-question", SAMPLE_ANSWER.question));

  const answer = el("p", "preview-answer");
  for (const part of SAMPLE_ANSWER.answer) {
    if (part[0] === "bold") {
      answer.appendChild(el("strong", "", part[1]));
    } else if (part[0] === "cite") {
      answer.appendChild(el("span", "cite", part[1]));
    } else {
      answer.appendChild(document.createTextNode(part[1]));
    }
  }
  preview.appendChild(answer);

  const sources = el("ol", "preview-sources");
  for (const source of SAMPLE_ANSWER.sources) {
    const item = el("li", "kind-" + source[1]);
    item.appendChild(el("span", "source-number", source[0]));

    const words = el("div");
    words.appendChild(el("p", "preview-source-title", source[2]));
    const label = el("p", "preview-source-label");
    label.appendChild(el("span", "kind-dot"));
    label.appendChild(document.createTextNode(source[3]));
    words.appendChild(label);
    item.appendChild(words);

    sources.appendChild(item);
  }
  preview.appendChild(sources);

  preview.appendChild(el("figcaption", "", "A real answer from the LangGraph evaluation set"));
  return preview;
}


function buildSteps() {
  const steps = el("ol", "steps");
  for (let index = 0; index < STEPS.length; index++) {
    const item = el("li");
    item.appendChild(el("span", "step-number", index + 1));
    item.appendChild(el("strong", "", STEPS[index][0]));
    item.appendChild(el("span", "", STEPS[index][1]));
    steps.appendChild(item);
  }
  return steps;
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
    item.appendChild(el("span", "kind-dot"));
    item.appendChild(el("span", "", source.name));
    item.appendChild(el("strong", "", source.documents));
    connectors.appendChild(item);
  }
  info.appendChild(connectors);
  row.appendChild(info);

  const actions = el("div", "workspace-actions");
  const askButton = el("button", "button quiet", "Ask");
  askButton.type = "button";
  askButton.addEventListener("click", function () {
    openWorkspace(workspace.id, "ask");
  });
  const sourcesButton = el("button", "button quiet", "Sources");
  sourcesButton.type = "button";
  sourcesButton.addEventListener("click", function () {
    openWorkspace(workspace.id, "sources");
  });
  actions.appendChild(askButton);
  actions.appendChild(sourcesButton);

  const deleteButton = el("button", "button quiet danger writes");
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
