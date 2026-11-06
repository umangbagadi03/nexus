import * as api from "../api.js";
import { clear, el } from "../dom.js";
import { percent } from "../format.js";
import { state } from "../state.js";

const PIPELINE_NOTES = {
  baseline: "Small chunks, vector search only",
  hybrid: "Sections, vector + keyword search, reranker",
  agentic: "Hybrid, plus link graph, grading and retries",
};

let pageHolder = null;
let pollTimer = null;


export function renderEvalsPage(container) {
  pageHolder = el("div");
  container.appendChild(pageHolder);
  loadAndRender();
}


async function loadAndRender() {
  let evals;
  try {
    evals = await api.getEvals(state.workspace.id);
  } catch (error) {
    clear(pageHolder);
    pageHolder.appendChild(el("p", "notice", error.message));
    return;
  }

  if (!document.body.contains(pageHolder)) {
    return;
  }
  clear(pageHolder);

  if (evals.questions === 0) {
    pageHolder.appendChild(el("p", "empty",
      "This workspace has no evaluation questions yet. Add them to evals/" + state.workspace.id + "/questions.jsonl."));
    return;
  }

  const intro = evals.questions + " questions with hand-written reference answers: " +
    evals.single_hop + " answered by one document, " + evals.multi_hop + " that need two linked documents. " +
    "Each pipeline adds one improvement on top of the previous one, so the table shows what each step is worth.";
  pageHolder.appendChild(el("p", "section-intro", intro));

  pageHolder.appendChild(buildFullBlock(evals.full));
  pageHolder.appendChild(buildRetrievalBlock(evals.retrieval, evals.running));

  // While an eval runs, refresh to show progress and the new result
  clearTimeout(pollTimer);
  if (evals.running) {
    pollTimer = setTimeout(loadAndRender, 2000);
  }
}


function metricCell(value) {
  const cell = el("td");
  const metric = el("div", "metric");
  metric.appendChild(el("span", "metric-value", percent(value)));

  const bar = el("div", "metric-bar");
  const fill = el("span");
  let width = 0;
  if (value !== null && value !== undefined) {
    width = Math.round(value * 100);
  }
  fill.style.width = width + "%";
  bar.appendChild(fill);
  metric.appendChild(bar);

  cell.appendChild(metric);
  return cell;
}


function pipelineCell(name) {
  const cell = el("td", "pipeline-name", name);
  cell.appendChild(el("small", "", PIPELINE_NOTES[name]));
  return cell;
}


function headerRow(titles) {
  const row = el("tr");
  for (const title of titles) {
    row.appendChild(el("th", "", title));
  }
  return row;
}


function buildFullBlock(rows) {
  const block = el("section", "eval-block");
  block.appendChild(el("h2", "section-title", "Answer quality"));

  if (rows.length === 0) {
    block.appendChild(el("p", "eval-note", "No full runs yet. They call the LLM for every question, so they run from the terminal:"));
    block.appendChild(el("p", "eval-note"));
    block.lastChild.appendChild(el("code", "", "python main.py eval " + state.workspace.id + " --pipeline agentic"));
    return block;
  }

  const table = el("table", "eval-table");
  table.appendChild(headerRow(["Pipeline", "Source recall", "Answer accuracy", "Fact coverage", "Single-document", "Linked documents", "Avg time"]));

  for (const row of rows) {
    const tableRow = el("tr");
    tableRow.appendChild(pipelineCell(row.pipeline));
    tableRow.appendChild(metricCell(row.recall));
    tableRow.appendChild(metricCell(row.accuracy));
    tableRow.appendChild(metricCell(row.coverage));
    tableRow.appendChild(metricCell(row.single_hop_accuracy));
    tableRow.appendChild(metricCell(row.multi_hop_accuracy));
    tableRow.appendChild(el("td", "", Math.round(row.average_seconds * 10) / 10 + " s"));
    table.appendChild(tableRow);
  }
  block.appendChild(table);

  const models = [];
  for (const row of rows) {
    if (row.model && !models.includes(row.model)) {
      models.push(row.model);
    }
  }
  block.appendChild(el("p", "eval-note",
    "Answers judged against the reference answers by " + models.join(", ") + ". Run again from the terminal with python main.py eval."));
  return block;
}


function buildRetrievalBlock(rows, running) {
  const block = el("section", "eval-block");
  block.appendChild(el("h2", "section-title", "Retrieval only"));
  block.appendChild(el("p", "eval-note",
    "Checks whether the right documents are found, without calling the LLM. It is free, so run it after every change."));

  const actions = el("div", "eval-actions");
  for (const pipeline of ["baseline", "hybrid"]) {
    const button = el("button", "button quiet", "Run " + pipeline);
    button.type = "button";
    button.disabled = Boolean(running);
    button.addEventListener("click", async function () {
      try {
        await api.runEval(state.workspace.id, pipeline);
      } catch (error) {
        window.alert(error.message);
      }
      loadAndRender();
    });
    actions.appendChild(button);
  }

  if (running) {
    const status = el("span", "eval-running");
    status.appendChild(el("span", "spinner"));
    status.appendChild(document.createTextNode(running.pipeline + ": " + running.message));
    actions.appendChild(status);
  }
  block.appendChild(actions);

  if (rows.length > 0) {
    const table = el("table", "eval-table");
    table.appendChild(headerRow(["Pipeline", "Source recall", "Questions"]));
    for (const row of rows) {
      const tableRow = el("tr");
      tableRow.appendChild(pipelineCell(row.pipeline));
      tableRow.appendChild(metricCell(row.recall));
      tableRow.appendChild(el("td", "", row.questions));
      table.appendChild(tableRow);
    }
    block.appendChild(table);
  }

  return block;
}
