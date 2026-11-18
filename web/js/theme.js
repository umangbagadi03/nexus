// Light or dark. With no choice saved, the page follows the system setting.
// The choice is saved in this browser, and applied in index.html before the page draws.

import { icon } from "./icons.js";

const STORAGE_KEY = "nexus-theme";
const systemDark = window.matchMedia("(prefers-color-scheme: dark)");
const button = document.getElementById("theme-toggle");


function currentTheme() {
  const chosen = document.documentElement.dataset.theme;
  if (chosen === "dark" || chosen === "light") {
    return chosen;
  }
  if (systemDark.matches) {
    return "dark";
  }
  return "light";
}


function showButton() {
  // The button shows what a click switches to
  let next = "dark";
  let iconName = "moon";
  if (currentTheme() === "dark") {
    next = "light";
    iconName = "sun";
  }

  button.replaceChildren(icon(iconName));
  button.title = "Switch to " + next + " mode";
  button.setAttribute("aria-label", "Switch to " + next + " mode");
}


export function setUpThemeToggle() {
  showButton();

  button.addEventListener("click", function () {
    let next = "dark";
    if (currentTheme() === "dark") {
      next = "light";
    }
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch (error) {
      // Private windows can block storage, the choice then lasts until the page reloads
    }
    showButton();
  });

  // If the reader never picked, follow the system when it changes
  systemDark.addEventListener("change", showButton);
}
