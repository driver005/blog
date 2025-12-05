import argparse
import base64
import json
import os

import frontmatter
import markdown
import requests
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# CLI overrides
parser = argparse.ArgumentParser()
parser.add_argument("--url", default=os.getenv("WP_BASE_URL"))
parser.add_argument("--user", default=os.getenv("WP_USER"))
parser.add_argument("--passw", default=os.getenv("WP_PASS"))
args = parser.parse_args()

WP_URL = str(args.url or "").rstrip("/")
WP_USER = args.user
WP_PASS = args.passw

AUTH = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HEADERS = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}

CONTENT_DIR = "content"


# ---------------------------------------------
# WordPress helpers
# ---------------------------------------------
def ensure_category(name):
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
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={name}", headers=HEADERS)
    data = r.json()
    if isinstance(data, list) and data:
        return data[0]["id"]

    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/tags",
        headers=HEADERS,
        data=json.dumps({"name": name}),
    )
    return r.json()["id"]


def upload_image_ret_meta(image_path):
    """Upload and return FULL metadata including ID and URL."""
    fname = os.path.basename(image_path)
    with open(image_path, "rb") as f:
        img_data = f.read()

    headers = {
        "Authorization": f"Basic {AUTH}",
        "Content-Disposition": f"attachment; filename={fname}",
        "Content-Type": "image/jpeg" if fname.lower().endswith(".jpg") else "image/png",
    }

    r = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, data=img_data)
    r.raise_for_status()
    return r.json()  # contains id, source_url, etc.


def find_existing_post(slug):
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

    # Image handling
    images = [
        f for f in os.listdir(post_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ]

    uploaded_images = {}
    for img in images:
        img_path = os.path.join(post_dir, img)
        result = upload_image_ret_meta(img_path)
        uploaded_images[img] = result
        raw_md = raw_md.replace(img, result["source_url"])

    # Featured image logic
    featured_media_id = None
    featured_image_name = post_md.get("featured_image")  # optional

    if featured_image_name and featured_image_name in uploaded_images:
        featured_media_id = uploaded_images[featured_image_name]["id"]
    elif images:
        # fallback: first image
        first = images[0]
        featured_media_id = uploaded_images[first]["id"]

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

    if featured_media_id:
        post_data["featured_media"] = featured_media_id

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
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers=HEADERS,
            data=json.dumps(post_data),
        )

    print(r.status_code, r.text)
