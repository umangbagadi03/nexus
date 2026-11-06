const KIND_NAMES = {
  docs: ["page", "pages"],
  issue: ["issue", "issues"],
  pr: ["pull request", "pull requests"],
  file: ["file", "files"],
  note: ["pushed document", "pushed documents"],
};

export function kindName(kind, count) {
  const names = KIND_NAMES[kind] || ["document", "documents"];
  if (count === 1) {
    return names[0];
  }
  return names[1];
}

export function percent(value) {
  if (value === null || value === undefined) {
    return "n/a";
  }
  return Math.round(value * 1000) / 10 + "%";
}

export function timeAgo(isoText) {
  if (!isoText) {
    return "never";
  }

  const seconds = Math.round((Date.now() - new Date(isoText).getTime()) / 1000);
  if (seconds < 60) {
    return "just now";
  }

  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return minutes + " min ago";
  }

  const hours = Math.round(minutes / 60);
  if (hours === 1) {
    return "1 hour ago";
  }
  if (hours < 24) {
    return hours + " hours ago";
  }

  const days = Math.round(hours / 24);
  if (days === 1) {
    return "1 day ago";
  }
  return days + " days ago";
}
