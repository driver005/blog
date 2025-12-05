import base64
import json
import os

import frontmatter
import markdown
import requests

WP_URL = str(os.getenv("vars.WP_BASE_URL") or "").rstrip("/")
WP_USER = os.getenv("vars.WP_USER")
WP_PASS = os.getenv("secrects.WP_PASS")

AUTH = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}

CONTENT_DIR = "content"


# ---------------------------------------------
# WordPress helpers
# ---------------------------------------------
def ensure_category(name):
    """Creates a category if missing and returns ID."""
    print(WP_URL)
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories?search={name}", headers=HEADERS
    )
    data = r.json()
    if isinstance(data, list) and data:
        return data[0]["id"]

    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/categories",
        headers=HEADERS,
        data=json.dumps({"name": name}),
    )
    return r.json()["id"]


def ensure_tag(name):
    """Creates a tag if missing and returns ID."""
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={name}", headers=HEADERS)
    data = r.json()
    if isinstance(data, list) and data:
        return data[0]["id"]

    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/tags", headers=HEADERS, data=json.dumps({"name": name})
    )
    return r.json()["id"]


def upload_image(image_path):
    """Uploads an image to WordPress."""
    fname = os.path.basename(image_path)
    with open(image_path, "rb") as f:
        img_data = f.read()

    headers = {
        "Authorization": f"Basic {AUTH}",
        "Content-Disposition": f"attachment; filename={fname}",
        "Content-Type": "image/jpeg" if fname.endswith(".jpg") else "image/png",
    }

    r = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, data=img_data)
    r.raise_for_status()
    return r.json()["source_url"]


def find_existing_post(slug):
    """Returns existing post ID if found."""
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts?slug={slug}", headers=HEADERS)
    posts = r.json()
    if isinstance(posts, list) and posts:
        return posts[0]["id"]
    return None


# ---------------------------------------------
# Main publishing logic
# ---------------------------------------------
for root, dirs, files in os.walk(CONTENT_DIR):
    if "index.md" not in files:
        continue

    md_path = os.path.join(root, "index.md")
    post_dir = root

    post_md = frontmatter.load(md_path)

    title = post_md.get("title", "Untitled")
    slug = post_md.get("slug", os.path.basename(root))
    status = post_md.get("status", "draft")

    raw_md = post_md.content

    # Upload images in directory
    images = [
        f for f in os.listdir(post_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    for img in images:
        img_path = os.path.join(post_dir, img)
        wp_url = upload_image(img_path)
        raw_md = raw_md.replace(img, wp_url)

    # Convert Markdown → HTML
    html = markdown.markdown(raw_md)

    # Categories & Tags
    categories = [ensure_category(c) for c in post_md.get("categories", [])]
    tags = [ensure_tag(t) for t in post_md.get("tags", [])]

    post_data = {
        "title": title,
        "slug": slug,
        "content": html,
        "status": status,
        "categories": categories,
        "tags": tags,
    }

    existing = find_existing_post(slug)

    if existing:
        print(f"Updating post: {slug}")
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{existing}",
            headers=HEADERS,
            data=json.dumps(post_data),
        )
    else:
        print(f"Creating new post: {slug}")
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts", headers=HEADERS, data=json.dumps(post_data)
        )

    print(r.status_code, r.text)
