#!/usr/bin/env python3
"""
Push Markdown content to WordPress with:

✔ Category descriptions
✔ Category icons (custom meta field)
✔ Tag descriptions
✔ Image upload with skip-if-exists
✔ Featured image support
✔ Featured image ALT TEXT support
✔ Markdown → HTML
✔ Full logging support
✔ Proper main() loop
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

log = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Logging setup
# -------------------------------------------------------------------
def setup_logging(log_file=None, level=logging.INFO):
    """
    Configure logging.
    If log_file is None → no file logging.
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove old handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console)

    # File logging only if enabled
    if log_file:
        file = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file.setLevel(level)
        file.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file)

    logger.debug(
        "Logging initialized (file logging: %s)"
        % (log_file if log_file else "DISABLED")
    )


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
        "Content-Type": ("image/jpeg" if fname.endswith(".jpg") else "image/png"),
    }

    r = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, data=img_data)
    r.raise_for_status()

    media = r.json()
    return media["id"], media["source_url"]


def set_media_alt_text(media_id, alt_text):
    """Set ALT TEXT for an uploaded image."""
    log.info(f"→ Setting ALT text for media {media_id}: {alt_text}")

    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/media/{media_id}",
        headers=HEADERS,
        data=json.dumps({"alt_text": alt_text}),
    )

    if r.status_code >= 300:
        log.error(f"Failed to update ALT text: {r.text[:150]}")


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
# MAIN LOOP
# ===================================================================
def main():
    global WP_URL, WP_USER, WP_PASS, AUTH, HEADERS, CONTENT_DIR

    # Load environment & arguments -----------------------------------
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.getenv("WP_BASE_URL"))
    parser.add_argument("--user", default=os.getenv("WP_USER"))
    parser.add_argument("--passw", default=os.getenv("WP_PASS"))
    parser.add_argument(
        "--log-file",
        nargs="?",
        const="wp_push.log",
        default=None,
        help="Enable file logging. Optionally provide a custom file name.",
    )
    args = parser.parse_args()

    WP_URL = str(args.url or "").rstrip("/")
    WP_USER = args.user
    WP_PASS = args.passw

    AUTH = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    HEADERS = {"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"}
    CONTENT_DIR = "content"

    setup_logging(args.log_file)

    log.info(f"Using WordPress: {WP_URL}")
    log.info(f"Content directory: {os.path.abspath(CONTENT_DIR)}")

    # Walk content directory -----------------------------------------
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
        fm_featured_alt = post_md.get("featured_alt")

        if fm_featured:
            fp = os.path.join(root, fm_featured)
            log.info(f"Featured image from front-matter: {fm_featured}")
            featured_media_id, _ = upload_image(fp)

            # set alt text
            if featured_media_id and fm_featured_alt:
                set_media_alt_text(featured_media_id, fm_featured_alt)

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


# ===================================================================
# ENTRY POINT
# ===================================================================
if __name__ == "__main__":
    main()
