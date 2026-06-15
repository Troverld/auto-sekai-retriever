export function toImgNewPath(path) {
  return `/img_new/${path.toLowerCase()}`;
}

export function normalizeImageKey(path) {
  return (
    path
      .split("/")
      .pop()
      ?.replace(".png", "")
      .toLowerCase() ?? ""
  );
}
