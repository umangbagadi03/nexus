// el("p", "intro", "Hello") creates <p class="intro">Hello</p>.
// Text is always set with textContent, so nothing from the server is ever run as HTML.
export function el(tag, className, text) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (text !== undefined && text !== null) {
    element.textContent = text;
  }
  return element;
}

export function clear(element) {
  while (element.firstChild) {
    element.removeChild(element.firstChild);
  }
}
