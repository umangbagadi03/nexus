// All calls to the Nexus server. Errors come back as an Error with the server's message.

async function request(method, path, body) {
  const options = { method: method, headers: {} };

  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    throw new Error("Could not reach the Nexus server. Check that `python main.py serve` is running.");
  }

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong.");
  }
  return data;
}

export function getStatus() {
  return request("GET", "/api/status");
}

export function listWorkspaces() {
  return request("GET", "/api/workspaces");
}

export function createWorkspace(name, description) {
  return request("POST", "/api/workspaces", { name: name, description: description });
}

export function deleteWorkspace(workspaceId) {
  return request("DELETE", "/api/workspaces/" + workspaceId);
}

export function getWorkspace(workspaceId) {
  return request("GET", "/api/workspaces/" + workspaceId);
}

export function ask(workspaceId, question, pipeline) {
  return request("POST", "/api/workspaces/" + workspaceId + "/ask", { question: question, pipeline: pipeline });
}

// Calls onEvent for each event the server sends while it works on the answer
export async function askStream(workspaceId, question, pipeline, onEvent) {
  let response;
  try {
    response = await fetch("/api/workspaces/" + workspaceId + "/ask/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, pipeline: pipeline }),
    });
  } catch (error) {
    throw new Error("Could not reach the Nexus server. Check that `python main.py serve` is running.");
  }

  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "Something went wrong.");
  }

  // Events arrive one per line, but a read can stop in the middle of a line
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let unfinishedLine = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    const lines = (unfinishedLine + decoder.decode(value, { stream: true })).split("\n");
    unfinishedLine = lines.pop();
    for (const line of lines) {
      if (line) {
        onEvent(JSON.parse(line));
      }
    }
  }
}

export function uploadFiles(workspaceId, files, sourceName) {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  form.append("source_name", sourceName);
  return request("POST", "/api/workspaces/" + workspaceId + "/sources/upload", form);
}

export function addGitHubIssues(workspaceId, settings) {
  return request("POST", "/api/workspaces/" + workspaceId + "/sources/github-issues", settings);
}

export function addMarkdownRepo(workspaceId, settings) {
  return request("POST", "/api/workspaces/" + workspaceId + "/sources/markdown-repo", settings);
}

export function syncSource(workspaceId, sourceId) {
  return request("POST", "/api/workspaces/" + workspaceId + "/sources/" + sourceId + "/sync");
}

export function removeSource(workspaceId, sourceId) {
  return request("DELETE", "/api/workspaces/" + workspaceId + "/sources/" + sourceId);
}

export function getEvals(workspaceId) {
  return request("GET", "/api/workspaces/" + workspaceId + "/evals");
}

export function runEval(workspaceId, pipeline) {
  return request("POST", "/api/workspaces/" + workspaceId + "/evals/run", { pipeline: pipeline, retrieval_only: true });
}
