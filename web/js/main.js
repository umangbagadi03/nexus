import * as api from "./api.js";
import { clear, el } from "./dom.js";
import { kindName, timeAgo } from "./format.js";
import { fillIcons } from "./icons.js";
import { setUpModelPanel } from "./model.js";
import { setUpThemeToggle } from "./theme.js";
import { renderAskPage, showResult } from "./pages/ask.js";
import { renderEvalsPage } from "./pages/evals.js";
import { renderHomePage } from "./pages/home.js";
import { renderSourcesPage } from "./pages/sources.js";
import { state } from "./state.js";

const pageContainer = document.getElementById("page");
const pageHeader = document.getElementById("page-header");
const workspaceSelect = document.getElementById("workspace-select");

const PAGES = {
  home: renderHomePage,
  ask: renderAskPage,
  sources: renderSourcesPage,
  evals: renderEvalsPage,
};


function currentPageName() {
  const name = window.location.hash.replace("#/", "");
  if (PAGES[name]) {
    return name;
  }
  return "home";
}


function renderPage() {
  const pageName = currentPageName();

  for (const link of document.querySelectorAll(".sidebar .nav a")) {
    if (link.dataset.page === pageName) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  }

  // The home page has its own heading, workspace pages show the workspace name
  pageHeader.hidden = pageName === "home";

  clear(pageContainer);
  if (pageName === "home" || state.workspace) {
    PAGES[pageName](pageContainer);
  }
}


export function renderSidebar() {
  const workspace = state.workspace;
  if (!workspace) {
    return;
  }

  document.getElementById("workspace-name").textContent = workspace.name;
  document.getElementById("workspace-description").textContent = workspace.description;
  document.getElementById("nav-sources-count").textContent = workspace.sources.length;
  document.title = workspace.name + " - Nexus";
  workspaceSelect.value = workspace.id;

  renderWorkspaceStats(workspace);
  renderRecentQuestions();
}


// Under the workspace name: what it holds, and when it was last synced
function renderWorkspaceStats(workspace) {
  const list = document.getElementById("workspace-stats");
  clear(list);

  for (const kind of Object.keys(workspace.counts)) {
    const count = workspace.counts[kind];
    const item = el("li", "kind-" + kind);
    item.appendChild(el("span", "kind-dot"));
    item.appendChild(el("strong", "", count));
    item.appendChild(document.createTextNode(" " + kindName(kind, count)));
    list.appendChild(item);
  }

  let newest = "";
  for (const source of workspace.sources) {
    if (source.last_synced && source.last_synced > newest) {
      newest = source.last_synced;
    }
  }
  if (newest) {
    list.appendChild(el("li", "stats-synced", "Synced " + timeAgo(newest)));
  }
}


function renderRecentQuestions() {
  const recent = state.recent[state.workspace.id] || [];
  const box = document.getElementById("recent");
  const list = document.getElementById("recent-list");

  clear(list);
  box.hidden = recent.length === 0;

  for (const result of recent) {
    const item = el("li");
    const button = el("button", "", result.question);
    button.title = result.question;
    button.addEventListener("click", function () {
      window.location.hash = "#/ask";
      showResult(result);
    });
    item.appendChild(button);
    list.appendChild(item);
  }
}


// Pages call this after something changed on the server, like a sync finishing
export async function reloadWorkspace() {
  state.workspace = await api.getWorkspace(state.workspace.id);
  renderSidebar();
  return state.workspace;
}


export async function reloadWorkspaceList() {
  state.workspaces = await api.listWorkspaces();

  clear(workspaceSelect);
  for (const workspace of state.workspaces) {
    const option = el("option", "", workspace.name);
    option.value = workspace.id;
    workspaceSelect.appendChild(option);
  }

  if (state.workspace) {
    workspaceSelect.value = state.workspace.id;
  }
  return state.workspaces;
}


// Open a workspace on one of its pages, for example "ask" or "sources"
export async function openWorkspace(workspaceId, pageName) {
  state.workspace = await api.getWorkspace(workspaceId);
  try {
    localStorage.setItem("nexus-workspace", workspaceId);
  } catch (error) {
    // Private windows can block storage, the app works without it
  }
  renderSidebar();

  const newHash = "#/" + pageName;
  if (window.location.hash === newHash) {
    renderPage();
  } else {
    window.location.hash = newHash;
  }
}


function savedWorkspaceId() {
  try {
    return localStorage.getItem("nexus-workspace");
  } catch (error) {
    return null;
  }
}


async function start() {
  fillIcons(document);
  setUpThemeToggle();

  try {
    state.status = await api.getStatus();
    setUpModelPanel();
    // A public demo hides everything that changes data
    document.body.classList.toggle("read-only", state.status.read_only);
    await reloadWorkspaceList();
  } catch (error) {
    pageContainer.appendChild(el("p", "notice", error.message));
    return;
  }

  // Start with the workspace used last time, or the first one
  if (state.workspaces.length > 0) {
    let firstId = state.workspaces[0].id;
    const savedId = savedWorkspaceId();
    for (const workspace of state.workspaces) {
      if (workspace.id === savedId) {
        firstId = savedId;
      }
    }
    state.workspace = await api.getWorkspace(firstId);
    renderSidebar();
  }

  workspaceSelect.addEventListener("change", function () {
    let pageName = currentPageName();
    if (pageName === "home") {
      pageName = "ask";
    }
    openWorkspace(workspaceSelect.value, pageName);
  });
  window.addEventListener("hashchange", renderPage);

  renderPage();
}

start();
