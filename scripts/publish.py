import argparse
import base64
import json
import os

import frontmatter
import markdown
import requests
from dotenv import load_dotenv

load_dotenv()


# -------------------------------------------------------
# LOGGING
# -------------------------------------------------------
def log(msg):
    print(f"[INFO] {msg}")


def warn(msg):
    print(f"[WARN] {msg}")


def err(msg):
    print(f"[ERROR] {msg}")


# -------------------------------------------------------
# WORDPRESS HELPERS
# -------------------------------------------------------
def wp_get(base_url, auth, endpoint, params=None):
    r = requests.get(f"{base_url}/wp-json/wp/v2/{endpoint}", auth=auth, params=params)
    r.raise_for_status()
    return r.json()


def wp_post(base_url, auth, endpoint, data):
    r = requests.post(f"{base_url}/wp-json/wp/v2/{endpoint}", auth=auth, json=data)
    r.raise_for_status()
    return r.json()


def wp_upload_image(base_url, auth, path, alt_text=None):
    filename = os.path.basename(path)

    # Check if image already exists in media library
    existing = wp_get(base_url, auth, "media", params={"search": filename})
    for item in existing:
        if item["title"]["rendered"] == filename:
            log(f"Reusing existing image: {filename}")
            media_id = item["id"]

            # Update alt text if provided
            if alt_text:
                requests.post(
                    f"{base_url}/wp-json/wp/v2/media/{media_id}",
                    auth=auth,
                    json={"alt_text": alt_text},
                )
            return media_id

    log(f"Uploading new image: {filename}")
    with open(path, "rb") as f:
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "image/jpeg",
        }
        r = requests.post(
            f"{base_url}/wp-json/wp/v2/media", auth=auth, headers=headers, data=f.read()
        )
    r.raise_for_status()
    media = r.json()

    # Set alt text
    if alt_text:
        requests.post(
            f"{base_url}/wp-json/wp/v2/media/{media['id']}",
            auth=auth,
            json={"alt_text": alt_text},
        )

    return media["id"]


# -------------------------------------------------------
# CATEGORY + TAG CREATION
# -------------------------------------------------------
def get_or_create_category(base_url, auth, name, description=None, icon=None):
    cats = wp_get(base_url, auth, "categories", params={"search": name})

    for c in cats:
        if c["name"].lower() == name.lower():
            log(f"Reusing category: {name}")

            update_data = {}
            if description and c.get("description") != description:
                update_data["description"] = description

            if icon and (c.get("meta") != [icon]):
                update_data["meta"] = [icon]

            if update_data:
                updated = requests.post(
                    f"{base_url}/wp-json/wp/v2/categories/{c['id']}",
                    auth=auth,
                    json=update_data,
                ).json()
                return updated["id"]

            return c["id"]

    log(f"Creating category: {name}")
    new_cat = wp_post(
        base_url,
        auth,
        "categories",
        {
            "name": name,
            "description": description or "",
            "meta": [icon] if icon else [],
        },
    )
    return new_cat["id"]


def get_or_create_tag(base_url, auth, name, description=None):
    tags = wp_get(base_url, auth, "tags", params={"search": name})

    for t in tags:
        if t["name"].lower() == name.lower():
            log(f"Reusing tag: {name}")

            if description and t.get("description") != description:
                updated = requests.post(
                    f"{base_url}/wp-json/wp/v2/tags/{t['id']}",
                    auth=auth,
                    json={"description": description},
                ).json()
                return updated["id"]

            return t["id"]

    log(f"Creating tag: {name}")
    new_tag = wp_post(
        base_url, auth, "tags", {"name": name, "description": description or ""}
    )
    return new_tag["id"]


# -------------------------------------------------------
# MAIN LOGIC
# -------------------------------------------------------
def process_file(base_url, auth, root, file_path):
    md = frontmatter.load(file_path)
    html_content = markdown.markdown(md.content)

    title = md.get("title") or "Untitled"

    categories = md.get("categories", [])
    category_descriptions = md.get("category_descriptions", {})
    category_icons = md.get("category_icons", {})

    tags = md.get("tags", [])
    tag_descriptions = md.get("tag_descriptions", {})

    images_alt = md.get("images", {})  # filename → alt text
    featured_image = md.get("featured_image")

    post_data = {"title": title, "content": html_content, "status": "publish"}

    # Categories
    if categories:
        cat_ids = []
        for c in categories:
            cid = get_or_create_category(
                base_url,
                auth,
                c,
                description=category_descriptions.get(c),
                icon=category_icons.get(c),
            )
            cat_ids.append(cid)
        post_data["categories"] = cat_ids

    # Tags
    if tags:
        tag_ids = []
        for t in tags:
            tid = get_or_create_tag(
                base_url, auth, t, description=tag_descriptions.get(t)
            )
            tag_ids.append(tid)
        post_data["tags"] = tag_ids

    # Featured image
    if featured_image:
        fp = os.path.join(root, featured_image)
        if os.path.exists(fp):
            alt = images_alt.get(featured_image) or os.path.splitext(featured_image)[
                0
            ].replace("-", " ")
            media_id = wp_upload_image(base_url, auth, fp, alt_text=alt)
            post_data["featured_media"] = media_id
        else:
            warn(f"Featured image not found: {fp}")

    # Publish post
    log("Publishing post…")
    response = wp_post(base_url, auth, "posts", post_data)
    log(f"Post published: ID={response['id']} URL={response['link']}")


# -------------------------------------------------------
# MAIN LOOP
# -------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.getenv("WP_BASE_URL"))
    parser.add_argument("--user", default=os.getenv("WP_USER"))
    parser.add_argument("--passw", default=os.getenv("WP_PASS"))
    parser.add_argument("--root", default=".")
    parser.add_argument("file")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    auth = (args.user, args.passw)
    root = args.root

    process_file(base_url, auth, root, args.file)


if __name__ == "__main__":
    main()
