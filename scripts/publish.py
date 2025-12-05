#!/usr/bin/env python3
import argparse
import base64
import json
import os

import frontmatter
import markdown
import requests
from dotenv import load_dotenv

# -------------------------------------------------------
# Load environment (.env + CLI)
# -------------------------------------------------------
load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--url", default=os.getenv("WP_BASE_URL"))
parser.add_argument("--user", default=os.getenv("WP_USER"))
parser.add_argument("--passw", default=os.getenv("WP_PASS"))
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args()

WP_URL = str(args.url or "").rstrip("/")
WP_USER = args.user
WP_PASS = args.passw
DRY_RUN = args.dry_run

CONTENT_DIR = "content"

AUTH = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
HEADERS_JSON = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}
HEADERS_MEDIA = {"Authorization": f"Basic {AUTH}"}


# -------------------------------------------------------
# Utility logging
# -------------------------------------------------------
def log(msg):
    print(f"[WP] {msg}")


# -------------------------------------------------------
# WordPress API helpers
# -------------------------------------------------------
def wp_get(path, params=None):
    return requests.get(f"{WP_URL}{path}", headers=HEADERS_JSON, params=params)


def wp_post(path, json_data=None):
    if DRY_RUN:
        log(f"(DRY RUN) POST {path} → {json_data}")
        return DummyResponse()
    return requests.post(f"{WP_URL}{path}", headers=HEADERS_JSON, json=json_data)


class DummyResponse:
    def json(self):
        return {}

    @property
    def status_code(self):
        return 200


# -------------------------------------------------------
# Image upload with deduplication
# -------------------------------------------------------
def upload_image(image_path):
    """Upload image only if not already uploaded."""
    fname = os.path.basename(image_path)

    # Check existing media by filename
    r = wp_get("/wp-json/wp/v2/media", params={"search": fname})
    if r.status_code == 200:
        for m in r.json():
            if m.get("title", {}).get("rendered") == fname:
                log(f"Image already exists: {fname} → {m['source_url']}")
                return m["id"], m["source_url"]

    # Upload new
    log(f"Uploading image: {fname}")
    if DRY_RUN:
        return -1, f"https://example.com/{fname}"

    with open(image_path, "rb") as f:
        img_data = f.read()

    headers = HEADERS_MEDIA.copy()
    headers["Content-Disposition"] = f"attachment; filename={fname}"

    r = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, data=img_data)
    r.raise_for_status()
    j = r.json()

    return j["id"], j["source_url"]


# -------------------------------------------------------
# Category with description support
# -------------------------------------------------------
def ensure_category(cat_spec):
    if isinstance(cat_spec, str):
        name = cat_spec
        description = ""
    else:
        name = cat_spec.get("name")
        description = cat_spec.get("description", "")

    # Lookup
    r = wp_get("/wp-json/wp/v2/categories", params={"search": name})
    if r.status_code == 200:
        for c in r.json():
            if c["name"].lower() == name.lower():
                cat_id = c["id"]

                # update description if necessary
                if description and c.get("description") != description:
                    log(f"Updating category description: {name}")
                    wp_post(
                        f"/wp-json/wp/v2/categories/{cat_id}",
                        json_data={"description": description},
                    )

                return cat_id

    # Create
    payload = {"name": name}
    if description:
        payload["description"] = description

    log(f"Creating category: {name}")
    r = wp_post("/wp-json/wp/v2/categories", json_data=payload)
    return r.json().get("id")


# -------------------------------------------------------
# Tags with description + slug + color support
# -------------------------------------------------------
def ensure_tag(tag_spec):
    """
    Tag object can be:
      - "Quantum"
      - {"name": "...", "slug": "...", "description": "...", "color": "#hex"}
    """

    if isinstance(tag_spec, str):
        name = tag_spec
        description = slug = color = None
    else:
        name = tag_spec.get("name")
        description = tag_spec.get("description")
        slug = tag_spec.get("slug")
        color = tag_spec.get("color")

    # lookup existing
    r = wp_get("/wp-json/wp/v2/tags", params={"search": name})
    if r.status_code == 200:
        for t in r.json():
            if t["name"].lower() == name.lower():
                tag_id = t["id"]

                # future update if WP supports it
                updates = {}
                if description and t.get("description") != description:
                    updates["description"] = description
                if slug and t.get("slug") != slug:
                    updates["slug"] = slug

                if updates:
                    log(f"Updating tag (future): {name}")
                    wp_post(f"/wp-json/wp/v2/tags/{tag_id}", json_data=updates)

                if color:
                    wp_post(
                        f"/wp-json/wp/v2/tags/{tag_id}",
                        json_data={"meta": {"color": color}},
                    )

                return tag_id

    # create new
    payload = {"name": name}
    if description:
        payload["description"] = description
    if slug:
        payload["slug"] = slug
    if color:
        payload["meta"] = {"color": color}

    log(f"Creating tag: {name}")
    r = wp_post("/wp-json/wp/v2/tags", json_data=payload)

    return r.json().get("id")


# -------------------------------------------------------
# Post lookup
# -------------------------------------------------------
def find_existing_post(slug):
    r = wp_get("/wp-json/wp/v2/posts", params={"slug": slug})
    posts = r.json()
    if isinstance(posts, list) and posts:
        return posts[0]["id"]
    return None


# -------------------------------------------------------
# MAIN PUBLISH LOOP
# -------------------------------------------------------
for root, dirs, files in os.walk(CONTENT_DIR):
    if "index.md" not in files:
        continue

    md_path = os.path.join(root, "index.md")
    post_dir = root

    post_md = frontmatter.load(md_path)

    title = post_md.get("title", "Untitled")
    slug = post_md.get("slug", os.path.basename(root))
    status = post_md.get("status", "draft")
    featured_image = post_md.get("featured_image")

    raw_md = post_md.content

    # Upload inline images
    for img in os.listdir(post_dir):
        if img.lower().endswith((".png", ".jpg", ".jpeg")):
            img_path = os.path.join(post_dir, img)
            img_id, img_url = upload_image(img_path)
            raw_md = raw_md.replace(img, img_url)

    # Featured image upload
    featured_media_id = None
    if featured_image:
        fpath = os.path.join(post_dir, featured_image)
        if os.path.exists(fpath):
            featured_media_id, _ = upload_image(fpath)
            log(f"Using featured image: {featured_image}")

    # Convert markdown → HTML
    html = markdown.markdown(raw_md)

    # Categories
    raw_cats = post_md.get("categories", [])
    categories = [ensure_category(c) for c in raw_cats]

    # Tags
    raw_tags = post_md.get("tags", [])
    tags = []
    for t in raw_tags:
        try:
            tid = ensure_tag(t)
            if tid:
                tags.append(tid)
        except Exception as e:
            log(f"Tag error for {t}: {e}")

    # Build post payload
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

    # Create or update
    existing = find_existing_post(slug)
    if existing:
        log(f"Updating post: {slug}")
        wp_post(f"/wp-json/wp/v2/posts/{existing}", json_data=post_data)
    else:
        log(f"Creating new post: {slug}")
        wp_post("/wp-json/wp/v2/posts", json_data=post_data)

log("Done.")
