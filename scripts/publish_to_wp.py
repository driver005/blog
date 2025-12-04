import os
import yaml
import json
import base64
import markdown
import requests
from pathlib import Path


WP_URL = os.getenv("WP_BASE_URL").rstrip("/")
WP_USER = os.getenv("WP_USER")
WP_PASS = os.getenv("WP_PASS")

AUTH = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()

HEADERS = {
    "Authorization": f"Basic {AUTH}",
    "Content-Type": "application/json"
}


def find_existing_post(slug: str):
    """Search for an existing WP post by slug."""
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts?slug={slug}", headers=HEADERS)
    if r.status_code == 200 and len(r.json()) > 0:
        return r.json()[0]["id"]
    return None


def upload_image(image_path: Path):
    """Upload an image to WordPress via REST API and return media ID."""
    filename = image_path.name
    headers = HEADERS.copy()
    headers["Content-Type"] = "image/jpeg" if filename.endswith(".jpg") else "image/png"
    headers["Content-Disposition"] = f"attachment; filename={filename}"

    with open(image_path, "rb") as f:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, data=f)
    r.raise_for_status()
    return r.json()["id"]


def process_markdown(md_path: Path):
    text = md_path.read_text(encoding="utf-8")

    # Extract YAML frontmatter
    meta = {}
    content_md = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        _, fm, content_md = parts
        meta = yaml.safe_load(fm)

    html = markdown.markdown(content_md)

    return meta, html


def publish_post(meta, html):
    slug = meta.get("slug")
    status = meta.get("status", "draft")

    post_data = {
        "title": meta.get("title", slug),
        "slug": slug,
        "content": html,
        "status": status
    }

    # Create or update?
    post_id = find_existing_post(slug)

    if post_id:
        print(f"Updating existing post: {slug} (ID {post_id})")
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
            headers=HEADERS,
            data=json.dumps(post_data)
        )
    else:
        print(f"Creating new post: {slug}")
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers=HEADERS,
            data=json.dumps(post_data)
        )

    print("Response:", r.status_code, r.text)


def main():
    content_dir = Path("content")

    for md_path in content_dir.glob("**/*.md"):
        print(f"Processing file: {md_path}")
        meta, html = process_markdown(md_path)

        if "slug" not in meta:
            print(f"ERROR: {md_path} has no slug in frontmatter. Skipping.")
            continue

        publish_post(meta, html)


if __name__ == "__main__":
    main()
