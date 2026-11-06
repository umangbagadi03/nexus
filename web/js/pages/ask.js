import * as api from "../api.js";
import { clear, el } from "../dom.js";
import { kindName } from "../format.js";
import { icon } from "../icons.js";
import { renderSidebar } from "../main.js";
import { CONNECTOR_INFO } from "./home.js";
import { rememberAnswer, state } from "../state.js";

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// The parts of the page that change after a question is asked
let questionInput = null;
let askButton = null;
let belowBox = null;


export function renderAskPage(container) {
  container.appendChild(buildAskBox());

  belowBox = el("div");
  container.appendChild(belowBox);

  belowBox.appendChild(buildStart());
}


function buildAskBox() {
  const form = el("form", "ask-box");

  questionInput = el("textarea");
  questionInput.rows = 2;
  questionInput.placeholder = "Ask anything about " + state.workspace.name;
  questionInput.setAttribute("aria-label", "Your question");
  form.appendChild(questionInput);

  const bottom = el("div", "ask-box-bottom");
  bottom.appendChild(buildPipelinePicker());

  askButton = el("button", "button", "Ask");
  askButton.type = "submit";
  bottom.appendChild(askButton);
  form.appendChild(bottom);

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    askQuestion(questionInput.value.trim());
  });

  // Enter sends the question, Shift+Enter adds a new line
  questionInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  return form;
}


function buildPipelinePicker() {
  const picker = el("fieldset", "pipeline-picker");
  picker.appendChild(el("legend", "", "Pipeline"));

  const options = [
    ["agentic", "Agentic"],
    ["hybrid", "Hybrid"],
    ["baseline", "Baseline"],
  ];

  for (const option of options) {
    const label = el("label");
    const input = el("input");
    input.type = "radio";
    input.name = "pipeline";
    input.value = option[0];
    if (option[0] === "agentic") {
      input.checked = true;
    }
    label.appendChild(input);
    label.appendChild(document.createTextNode(option[1]));
    picker.appendChild(label);
  }

  picker.title = "Agentic checks and retries its search. Hybrid and Baseline are simpler pipelines, kept for comparison.";
  return picker;
}


function selectedPipeline() {
  const checked = document.querySelector("input[name=pipeline]:checked");
  return checked.value;
}


// Before the first question: example questions, and the sources this workspace searches
function buildStart() {
  const start = el("div", "start");
  const workspace = state.workspace;

  if (workspace.total_documents === 0) {
    const empty = el("div", "empty-workspace");
    empty.appendChild(el("h2", "", "Nothing to search yet"));
    empty.appendChild(el("p", "",
      "Connect a source first: upload files, add docs from a Git repository, pull GitHub issues, or send documents through the API."));
    const link = el("a", "button", "Add a source");
    link.href = "#/sources";
    empty.appendChild(link);
    return empty;
  }

  const examplesBlock = el("div");
  if (workspace.example_questions.length > 0) {
    examplesBlock.appendChild(el("h2", "", "Try asking"));
  }
  const examples = el("ul", "examples");
  for (const question of workspace.example_questions) {
    const item = el("li");
    const button = el("button", "", question);
    button.type = "button";
    button.addEventListener("click", function () {
      questionInput.value = question;
      askQuestion(question);
    });
    item.appendChild(button);
    examples.appendChild(item);
  }
  examplesBlock.appendChild(examples);
  start.appendChild(examplesBlock);

  const contentsBlock = el("div");
  contentsBlock.appendChild(el("h2", "", "Searching these sources"));
  const contents = el("ul", "contents");

  for (const source of workspace.sources) {
    const connector = CONNECTOR_INFO[source.type];
    const item = el("li", "kind-" + connector.kind);
    item.title = connector.label;
    item.appendChild(icon(connector.icon));
    item.appendChild(el("span", "", source.name));
    item.appendChild(el("strong", "", source.documents));
    contents.appendChild(item);
  }
  contentsBlock.appendChild(contents);

  const counts = workspace.counts;
  const kindParts = [];
  for (const kind of Object.keys(counts)) {
    kindParts.push(counts[kind] + " " + kindName(kind, counts[kind]));
  }
  if (kindParts.length > 0) {
    contentsBlock.appendChild(el("p", "contents-total", "In total: " + kindParts.join(", ") + "."));
  }

  const manage = el("a", "contents-link", "Add or sync sources");
  manage.href = "#/sources";
  contentsBlock.appendChild(manage);
  start.appendChild(contentsBlock);

  return start;
}


async function askQuestion(question) {
  if (!question) {
    return;
  }

  const live = buildLiveView(question);
  clear(belowBox);
  belowBox.appendChild(live.view);

  askButton.disabled = true;
  askButton.textContent = "Asking";

  try {
    let result = null;
    await api.askStream(state.workspace.id, question, selectedPipeline(), function (event) {
      if (event.type === "status") {
        live.statusText.textContent = event.text;
      } else if (event.type === "step") {
        live.addStep(event.step);
      } else if (event.type === "token") {
        live.addText(event.text);
      } else if (event.type === "error") {
        throw new Error(event.message);
      } else if (event.type === "result") {
        result = event.result;
      }
    });

    if (!result) {
      throw new Error("The connection closed before the answer was finished.");
    }
    rememberAnswer(state.workspace.id, result);
    renderSidebar();
    showResult(result, false);
  } catch (error) {
    live.status.hidden = true;
    live.view.prepend(el("p", "notice live-error", error.message));
  } finally {
    askButton.disabled = false;
    askButton.textContent = "Ask";
  }
}


// What the page shows while the answer is being written
function buildLiveView(question) {
  const view = el("div", "result");
  view.appendChild(el("h2", "result-question", question));

  const answer = el("article", "answer");
  const body = el("div", "answer-body");
  answer.appendChild(body);

  const status = el("div", "thinking");
  status.appendChild(el("div", "thinking-bar"));
  const statusText = el("p", "", "Starting");
  status.appendChild(statusText);
  answer.appendChild(status);
  view.appendChild(answer);

  const evidence = el("aside", "evidence");
  const trailTitle = el("h2", "", "How it found this");
  trailTitle.hidden = true;
  const trail = el("ol", "trail");
  evidence.appendChild(trailTitle);
  evidence.appendChild(trail);
  view.appendChild(evidence);

  let text = "";
  let drawWaiting = false;

  // Pieces can arrive faster than the screen updates, so draw at most once per frame
  function drawAnswer() {
    drawWaiting = false;
    body.innerHTML = DOMPurify.sanitize(marked.parse(text));
  }

  return {
    view: view,
    status: status,
    statusText: statusText,
    addText: function (piece) {
      text += piece;
      if (!drawWaiting) {
        drawWaiting = true;
        requestAnimationFrame(drawAnswer);
      }
    },
    addStep: function (step) {
      trailTitle.hidden = false;
      trail.appendChild(buildStep(step));
    },
  };
}


export function showResult(result, animateSteps = true) {
  if (!belowBox || !document.body.contains(belowBox)) {
    return;
  }
  clear(belowBox);
  questionInput.value = "";

  const view = el("div", "result");
  view.appendChild(el("h2", "result-question", result.question));

  const answer = el("article", "answer");
  const body = el("div", "answer-body");
  body.innerHTML = DOMPurify.sanitize(marked.parse(result.answer));
  turnCitationsIntoButtons(body, result.sources.length);
  answer.appendChild(body);

  if (result.check) {
    answer.appendChild(buildCheck(result.check));
  }

  const meta = "Answered by " + result.model + " in " + result.seconds + " seconds, using the " +
    result.pipeline + " pipeline.";
  answer.appendChild(el("p", "answer-meta", meta));
  view.appendChild(answer);

  const evidence = el("aside", "evidence");
  if (result.steps.length > 0) {
    evidence.appendChild(el("h2", "", "How it found this"));
    evidence.appendChild(buildTrail(result.steps, animateSteps));
  }
  evidence.appendChild(el("h2", "", "Sources"));
  evidence.appendChild(buildSources(result.sources));
  view.appendChild(evidence);

  belowBox.appendChild(view);
}


// Replace "[2]" in the answer with a button that jumps to source 2.
// Only plain text is touched, so code like messages[0] stays as it is.
function turnCitationsIntoButtons(container, sourceCount) {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const textNodes = [];

  while (walker.nextNode()) {
    const node = walker.currentNode;
    const insideCode = node.parentElement.closest("code, pre");
    if (!insideCode && /\[\d+\]/.test(node.textContent)) {
      textNodes.push(node);
    }
  }

  for (const node of textNodes) {
    const parts = node.textContent.split(/(\[\d+\])/);
    const fragment = document.createDocumentFragment();

    for (const part of parts) {
      const match = part.match(/^\[(\d+)\]$/);
      let number = 0;
      if (match) {
        number = Number(match[1]);
      }

      if (number >= 1 && number <= sourceCount) {
        const button = el("button", "cite", number);
        button.type = "button";
        button.setAttribute("aria-label", "Go to source " + number);
        button.addEventListener("click", function () {
          highlightSource(number);
        });
        fragment.appendChild(button);
      } else {
        fragment.appendChild(document.createTextNode(part));
      }
    }

    node.replaceWith(fragment);
  }
}


function highlightSource(number) {
  const item = document.getElementById("source-" + number);
  if (!item) {
    return;
  }

  let behavior = "smooth";
  if (reduceMotion) {
    behavior = "auto";
  }
  item.scrollIntoView({ behavior: behavior, block: "center" });

  item.classList.add("highlight");
  setTimeout(function () {
    item.classList.remove("highlight");
  }, 900);
}


function buildStep(step) {
  const item = el("li", "step-" + step.kind, step.text);
  if (!reduceMotion) {
    item.classList.add("reveal");
  }
  return item;
}


function buildTrail(steps, animate) {
  const trail = el("ol", "trail");

  steps.forEach(function (step, index) {
    const item = buildStep(step);
    if (animate) {
      item.style.animationDelay = (index * 120) + "ms";
    } else {
      item.classList.remove("reveal");
    }
    trail.appendChild(item);
  });

  return trail;
}


// The result of the agent checking its answer against its sources
function buildCheck(check) {
  const block = el("div", "answer-check " + check.status);

  if (check.status === "passed") {
    block.appendChild(el("p", "", "Checked against the sources: every claim is supported."));
  } else if (check.status === "unknown") {
    block.appendChild(el("p", "", "This answer could not be checked against its sources."));
  } else {
    block.appendChild(el("p", "", "Check these claims. They may not be supported by the sources:"));
    const list = el("ul");
    for (const item of check.unsupported) {
      const row = el("li");
      row.appendChild(el("strong", "", item.claim));
      if (item.reason) {
        row.appendChild(document.createTextNode(" " + item.reason));
      }
      list.appendChild(row);
    }
    block.appendChild(list);
  }

  return block;
}


function buildSources(sources) {
  const list = el("ul", "sources");

  for (const source of sources) {
    const item = el("li", "source kind-" + source.kind);
    item.id = "source-" + source.citation;

    const link = el("a", "source-title");
    link.href = source.url;
    link.target = "_blank";
    link.rel = "noopener";
    link.appendChild(el("span", "source-number", source.citation));
    link.appendChild(document.createTextNode(source.title));
    item.appendChild(link);

    let label = source.label;
    if (source.via) {
      label += ". " + source.via;
    }
    item.appendChild(el("p", "source-label", label));
    item.appendChild(el("p", "source-snippet", cleanSnippet(source.snippet)));

    list.appendChild(item);
  }

  return list;
}


// Snippets are raw text from the source. Drop the "Title: ..." line added for indexing,
// heading markers, code fences, issue template checkboxes and lines the label already shows.
function cleanSnippet(text) {
  const kept = [];

  for (const rawLine of text.split("\n")) {
    let line = rawLine.trim();

    if (line === "" || line.startsWith("Title: ") || line.startsWith("```") || line.startsWith("Labels: ")) {
      continue;
    }
    if (line.startsWith("- [x]") || line.startsWith("- [ ]")) {
      continue;
    }
    if (/^(Issue|Pull request) #\d+/.test(line)) {
      continue;
    }

    line = line.replace(/^#+\s*/, "");
    line = line.replace(/\*\*/g, "");
    kept.push(line);
  }

  return kept.join(" ");
}
