#!/usr/bin/env python3
"""
Push Markdown content to WordPress with:

✔ Category descriptions
✔ Category icons (custom meta field)
✔ Tag descriptions
✔ Image upload with skip-if-exists
✔ Featured image support
✔ Markdown → HTML
✔ Full logging support
"""

import argparse
import base64
import json
import logging
import os

import frontmatter
import markdown
import requests
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Logging setup
# -------------------------------------------------------------------
LOG_FILE = "wp_sync.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)

log = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Load env vars
# -------------------------------------------------------------------
load_dotenv()

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

log.info(f"Using WordPress: {WP_URL}")
log.info(f"Content directory: {os.path.abspath(CONTENT_DIR)}")


# ===================================================================
# CATEGORY + TAG HELPERS
# ===================================================================
def ensure_category(cat):
    """Create/update category with description + icon."""
    if isinstance(cat, str):
        name = cat
        description = ""
        icon = None
    else:
        name = cat.get("name")
        description = cat.get("description", "")
        icon = cat.get("icon")

    log.info(f"Ensuring category exists: {name}")

    r = requests.get(
        f"{WP_URL}/wp-json/wp/v2/categories?search={name}", headers=HEADERS
    )
    data = r.json()

    if isinstance(data, list) and data:
        cat_id = data[0]["id"]
        log.info(f"→ Category exists [{cat_id}] {name}")

        update_data = {}
        if description and data[0].get("description") != description:
            update_data["description"] = description
        if icon:
            update_data["meta"] = {"category_icon": icon}

        if update_data:
            log.info(f"→ Updating category {name}")
            requests.post(
                f"{WP_URL}/wp-json/wp/v2/categories/{cat_id}",
                headers=HEADERS,
                data=json.dumps(update_data),
            )
        return cat_id

    # Create new category
    log.info(f"→ Creating new category: {name}")
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
    """Create/update tag with optional description."""
    if isinstance(tag, str):
        name = tag
        description = ""
    else:
        name = tag.get("name")
        description = tag.get("description", "")

    log.info(f"Ensuring tag exists: {name}")

    r = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={name}", headers=HEADERS)
    data = r.json()

    if isinstance(data, list) and data:
        tag_id = data[0]["id"]
        log.info(f"→ Tag exists [{tag_id}] {name}")

        if description and data[0].get("description") != description:
            log.info(f"→ Updating tag description: {name}")
            requests.post(
                f"{WP_URL}/wp-json/wp/v2/tags/{tag_id}",
                headers=HEADERS,
                data=json.dumps({"description": description}),
            )
        return tag_id

    log.info(f"→ Creating new tag: {name}")
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/tags",
        headers=HEADERS,
        data=json.dumps({"name": name, "description": description}),
    )
    return r.json()["id"]


# ===================================================================
# IMAGE HANDLING
# ===================================================================
def wp_find_existing_image(fname):
    """Find an existing image by filename."""
    log.debug(f"Searching for existing media: {fname}")

    r = requests.get(f"{WP_URL}/wp-json/wp/v2/media?search={fname}", headers=HEADERS)
    data = r.json()

    if isinstance(data, list) and data:
        log.info(f"→ Found existing media: {fname}")
        return data[0]
    return None


def upload_image(image_path):
    """
    Upload image unless existing.
    Returns (media_id, url)
    """
    fname = os.path.basename(image_path)
    log.info(f"Handling image: {fname}")

    existing = wp_find_existing_image(fname)
    if existing:
        log.info(f"→ Skipping upload, exists: {fname}")
        return existing["id"], existing["source_url"]

    try:
        with open(image_path, "rb") as f:
            img_data = f.read()
    except FileNotFoundError:
        log.error(f"Image not found: {image_path}")
        return None, None

    log.info(f"→ Uploading image: {fname}")

    headers = {
        "Authorization": f"Basic {AUTH}",
        "Content-Disposition": f"attachment; filename={fname}",
        "Content-Type": "image/jpeg" if fname.endswith(".jpg") else "image/png",
    }

    r = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, data=img_data)
    r.raise_for_status()

    media = r.json()
    return media["id"], media["source_url"]


# ===================================================================
# POST HELPERS
# ===================================================================
def find_existing_post(slug):
    """Return existing post ID if available."""
    log.debug(f"Searching for post: {slug}")
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts?slug={slug}", headers=HEADERS)
    posts = r.json()
    if isinstance(posts, list) and posts:
        log.info(f"→ Existing post found: {slug} [{posts[0]['id']}]")
        return posts[0]["id"]
    return None


# ===================================================================
# MAIN RUN LOOP
# ===================================================================
for root, dirs, files in os.walk(CONTENT_DIR):
    if "index.md" not in files:
        continue

    log.info(f"Processing folder: {root}")

    md_path = os.path.join(root, "index.md")
    post_md = frontmatter.load(md_path)

    title = post_md.get("title", "Untitled")
    slug = post_md.get("slug", os.path.basename(root))
    status = post_md.get("status", "draft")
    raw_md = post_md.content

    log.info(f"Post Title: {title}")
    log.info(f"Post Slug:  {slug}")

    # ---------------------------------------------------------------
    # Featured image
    # ---------------------------------------------------------------
    featured_media_id = None
    fm_featured = post_md.get("featured_image")

    if fm_featured:
        fp = os.path.join(root, fm_featured)
        log.info(f"Featured image from front-matter: {fm_featured}")
        featured_media_id, _ = upload_image(fp)

    # ---------------------------------------------------------------
    # Upload + replace images
    # ---------------------------------------------------------------
    for img in os.listdir(root):
        if img.lower().endswith((".png", ".jpg", ".jpeg")):
            img_path = os.path.join(root, img)
            media_id, url = upload_image(img_path)

            if media_id is None:
                continue

            if featured_media_id is None:
                featured_media_id = media_id

            raw_md = raw_md.replace(img, url)

    # Convert markdown to HTML
    html = markdown.markdown(raw_md)

    # ---------------------------------------------------------------
    # Categories & Tags
    # ---------------------------------------------------------------
    categories = [ensure_category(c) for c in post_md.get("categories", [])]
    tags = [ensure_tag(t) for t in post_md.get("tags", [])]

    # ---------------------------------------------------------------
    # Build post data
    # ---------------------------------------------------------------
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
        log.info(f"Featured media ID: {featured_media_id}")

    # ---------------------------------------------------------------
    # Create/update post
    # ---------------------------------------------------------------
    existing = find_existing_post(slug)

    if existing:
        log.info(f"Updating post: {slug}")
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts/{existing}",
            headers=HEADERS,
            data=json.dumps(post_data),
        )
    else:
        log.info(f"Creating new post: {slug}")
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers=HEADERS,
            data=json.dumps(post_data),
        )

    log.info(f"→ Response {r.status_code}: {r.text[:200]}")
