// Small line icons, drawn on a 24x24 grid. They use currentColor, so CSS sets their color.

const PATHS = {
  home: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  file: '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/>',
  ask: '<path d="M4 5h16v11H9l-5 4z"/><path d="M9 9.5h6M9 12.5h4"/>',
  sources: '<ellipse cx="12" cy="6" rx="7" ry="2.5"/><path d="M5 6v6c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V6"/><path d="M5 12v6c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-6"/>',
  evals: '<path d="M4 20h16"/><path d="M7 16v-5M12 16V6M17 16v-8"/>',
  upload: '<path d="M12 15V4M7.5 8.5 12 4l4.5 4.5"/><path d="M4 15v4h16v-4"/>',
  repo: '<circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="9" r="2"/><path d="M6 8v8M18 11c0 3-3 4-6 4H8"/>',
  issues: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="1.6"/>',
  api: '<path d="M8 8 4 12l4 4M16 8l4 4-4 4M13.5 6l-3 12"/>',
  sync: '<path d="M19 8a7.5 7.5 0 0 0-13-1.5L4 9"/><path d="M4 4v5h5"/><path d="M5 16a7.5 7.5 0 0 0 13 1.5L20 15"/><path d="M20 20v-5h-5"/>',
  remove: '<path d="M5 7h14M10 7V5h4v2M7 7l1 12h8l1-12"/>',
};

export function icon(name) {
  const svg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + PATHS[name] + '</svg>';
  const holder = document.createElement("span");
  holder.innerHTML = svg;
  return holder.firstChild;
}

// Fill every <span data-icon="..."> that is already in the HTML
export function fillIcons(root) {
  for (const placeholder of root.querySelectorAll("[data-icon]")) {
    placeholder.replaceWith(icon(placeholder.dataset.icon));
  }
}
