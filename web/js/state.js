// What the whole app needs to know. Pages read from here instead of passing things around.
export const state = {
  workspaces: [],
  workspace: null,      // the selected workspace, with its sources and counts
  status: null,         // which model the server uses
  recent: {},           // workspace id -> list of answered questions, newest first
};

export function rememberAnswer(workspaceId, result) {
  if (!state.recent[workspaceId]) {
    state.recent[workspaceId] = [];
  }

  const list = state.recent[workspaceId];
  list.unshift(result);
  if (list.length > 8) {
    list.pop();
  }
}
