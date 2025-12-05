import argparse
import base64
import json
import os

import frontmatter
import markdown
import requests
from dotenv import load_dotenv

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


# -------------------------------------------------------------------
# Category + Tag helpers WITH description + icon support
# -------------------------------------------------------------------
def ensure_category(cat):
    """
    cat can be:
      - string ("Technology")
      - dict {"name": "...", "description": "...", "icon": "..."}
    """
    if isinstance(cat, str):
        name = cat
        description = ""
        icon = None
    else:
        name = cat.get("name")
        description = cat.get("description", "")
        icon = cat.get("icon")

    # Check existing
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories?search={name}", headers=HEADERS
    )
    data = r.json()
    if isinstance(data, list) and data:
        cat_id = data[0]["id"]
        # Update description or icon if needed
        update_data = {}
        if description and data[0].get("description") != description:
            update_data["description"] = description
        if icon:
            # Save icon into meta
            update_data["meta"] = {"category_icon": icon}

        if update_data:
            requests.post(
                f"{WP_URL}/wp-json/wp/v2/categories/{cat_id}",
                headers=HEADERS,
                data=json.dumps(update_data),
            )

        return cat_id

    # Create category
    payload = {"name": name, "description": description}
    if icon:
        payload["meta"] = {"category_icon": icon}

    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/categories",
        headers=HEADERS,
        data=json.dumps(payload),
    )
    return r.json()["id"]


def ensure_tag(tag):
    """
    tag can be:
      - string ("Qubits")
      - dict {"name": "...", "description": "..."}
    """
    if isinstance(tag, str):
        name = tag
        description = ""
    else:
        name = tag.get("name")
        description = tag.get("description", "")

    r = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={name}", headers=HEADERS)
    data = r.json()
    if isinstance(data, list) and data:
        tag_id = data[0]["id"]

        # Update description if changed
        if description and data[0].get("description") != description:
            requests.post(
                f"{WP_URL}/wp-json/wp/v2/tags/{tag_id}",
                headers=HEADERS,
                data=json.dumps({"description": description}),
            )

        return tag_id

    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/tags",
        headers=HEADERS,
        data=json.dumps({"name": name, "description": description}),
    )
    return r.json()["id"]


# -------------------------------------------------------------------
# Image handling (with skip-if-exists)
# -------------------------------------------------------------------
def wp_find_existing_image(fname):
    """Search existing media by file name."""
    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/media?search={fname}",
        headers=HEADERS,
    )
    data = r.json()
    if isinstance(data, list) and data:
        return data[0]["source_url"]
    return None


def upload_image(image_path):
    """Upload image unless it already exists."""
    fname = os.path.basename(image_path)

    existing = wp_find_existing_image(fname)
    if existing:
        print(f"→ Skipping upload, already exists: {fname}")
        return existing

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


# -------------------------------------------------------------------
# Post helper
# -------------------------------------------------------------------
def find_existing_post(slug):
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts?slug={slug}", headers=HEADERS)
    posts = r.json()
    if isinstance(posts, list) and posts:
        return posts[0]["id"]
    return None


# -------------------------------------------------------------------
# Main logic
# -------------------------------------------------------------------
for root, dirs, files in os.walk(CONTENT_DIR):
    if "index.md" not in files:
        continue

    md_path = os.path.join(root, "index.md")
    post_md = frontmatter.load(md_path)

    title = post_md.get("title", "Untitled")
    slug = post_md.get("slug", os.path.basename(root))
    status = post_md.get("status", "draft")
    raw_md = post_md.content

    # Handle images
    for img in os.listdir(root):
        if img.lower().endswith((".png", ".jpg", ".jpeg")):
            img_path = os.path.join(root, img)
            url = upload_image(img_path)
            raw_md = raw_md.replace(img, url)

    html = markdown.markdown(raw_md)

    # Category + tag object support
    categories_front = post_md.get("categories", [])
    tags_front = post_md.get("tags", [])

    categories = [ensure_category(c) for c in categories_front]
    tags = [ensure_tag(t) for t in tags_front]

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
        print(f"Creating post: {slug}")
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers=HEADERS,
            data=json.dumps(post_data),
        )

    print(r.status_code, r.text)
