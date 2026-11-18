// The model panel at the bottom of the sidebar: which model answers, and a visitor's own API key.
// The key is kept in this browser tab only (sessionStorage) and sent with each question.
// The server uses it for that question and never stores it.

import { el } from "./dom.js";
import { state } from "./state.js";

const STORAGE_KEY = "nexus-own-model";

let visitorModel = null;   // { provider, api_key, model } or null

const toggle = document.getElementById("model-toggle");
const statusText = document.getElementById("model-status-text");
const form = document.getElementById("model-form");
const providerSelect = document.getElementById("model-provider");
const keyInput = document.getElementById("model-key");
const modelInput = document.getElementById("model-name");
const forgetButton = document.getElementById("model-forget");


function readSaved() {
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    if (saved) {
      return JSON.parse(saved);
    }
  } catch (error) {
    // Private windows can block storage, the key then lasts until the page reloads
  }
  return null;
}


function save(model) {
  try {
    if (model) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(model));
    } else {
      sessionStorage.removeItem(STORAGE_KEY);
    }
  } catch (error) {
    // Same as above
  }
}


function providerInfo(providerId) {
  for (const provider of state.status.providers) {
    if (provider.id === providerId) {
      return provider;
    }
  }
  return state.status.providers[0];
}


// What goes with each question: the visitor's model, or nothing so the server decides
export function ownModel() {
  return visitorModel;
}


function describe() {
  if (visitorModel) {
    const provider = providerInfo(visitorModel.provider);
    const model = visitorModel.model || provider.default_model;
    return "Your key: " + provider.label + " (" + model + ")";
  }
  if (state.status.search_only) {
    return "Search only, no model";
  }
  return state.status.model;
}


function showStatus() {
  const hasModel = Boolean(visitorModel) || !state.status.search_only;
  document.body.classList.toggle("has-model", hasModel);
  document.body.classList.toggle("no-model", !hasModel);

  statusText.textContent = describe();
  if (hasModel) {
    toggle.title = "Answers are written by " + describe().replace("Your key: ", "") + ". Click to change.";
  } else {
    toggle.title = "No model is connected, so questions return matching sources only. Click to add your own API key.";
  }
  forgetButton.hidden = !visitorModel;
}


function showDefaultModel() {
  modelInput.placeholder = providerInfo(providerSelect.value).default_model;
}


export function openModelForm() {
  form.hidden = false;
  toggle.setAttribute("aria-expanded", "true");
  toggle.scrollIntoView({ block: "nearest" });
  keyInput.focus();
}


function closeModelForm() {
  form.hidden = true;
  toggle.setAttribute("aria-expanded", "false");
}


export function setUpModelPanel() {
  for (const provider of state.status.providers) {
    const option = el("option", "", provider.label);
    option.value = provider.id;
    providerSelect.appendChild(option);
  }

  visitorModel = readSaved();
  if (visitorModel) {
    providerSelect.value = visitorModel.provider;
    modelInput.value = visitorModel.model;
  }
  showDefaultModel();
  showStatus();

  toggle.addEventListener("click", function () {
    if (form.hidden) {
      openModelForm();
    } else {
      closeModelForm();
    }
  });

  providerSelect.addEventListener("change", showDefaultModel);

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    const apiKey = keyInput.value.trim();
    if (!apiKey) {
      keyInput.focus();
      return;
    }

    visitorModel = {
      provider: providerSelect.value,
      api_key: apiKey,
      model: modelInput.value.trim(),
    };
    save(visitorModel);
    keyInput.value = "";
    showStatus();
    closeModelForm();
  });

  forgetButton.addEventListener("click", function () {
    visitorModel = null;
    save(null);
    keyInput.value = "";
    modelInput.value = "";
    showStatus();
  });
}
