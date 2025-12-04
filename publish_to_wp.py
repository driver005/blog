import os, re, yaml, base64, json, requests
from markdown import markdown
from slugify import slugify
from pathlib import Path

WP_URL = os.getenv("WP_URL").rstrip("/")
WP_USER = os.getenv("WP_USER")
WP_PASS = os.getenv("WP_APP_PASSWORD")

AUTH_HEADER = {
    "Authorization": "Basic " + base64.b64encode(
        f"{WP_USER}:{WP_PASS}".encode()
    ).decode()
}

# --------------------------
# WordPress helpers
# --------------------------

def wp_get(endpoint):
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/{endpoint}", headers=AUTH_HEADER)
    r.raise_for_status()
    return r.json()

def wp_post(endpoint, data):
    r = requests.post(
        f"{WP_URL}/wp-json/wp/v2/{endpoint}",
        headers={**AUTH_HEADER, "Content-Type": "application/json"},
        data=json.dumps(data),
    )
    r.raise_for_status()
    return r.json()

def wp_put(endpoint, data):
    r = requests.put(
        f"{WP_URL}/wp-json/wp/v2/{endpoint}",
        headers={**AUTH_HEADER, "Content-Type": "application/json"},
        data=json.dumps(data),
    )
    r.raise_for_status()
    return r.json()

def wp_upload_media(image_path):
    filename = os.path.basename(image_path)
    headers = {
        **AUTH_HEADER,
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "image/jpeg" if filename.endswith(".jpg") else "image/png",
    }
    with open(image_path, "rb") as f:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/media", headers=headers, data=f)
        r.raise_for_status()
        return r.json()["id"]

def wp_get_or_create_term(term_name, taxonomy):
    items = wp_get(f"{taxonomy}?search={term_name}")
    if items:
        return items[0]["id"]
    return wp_post(taxonomy, {"name": term_name})["id"]


# --------------------------
# Process Markdown Files
# --------------------------

def process_md_file(path):
    raw = Path(path).read_text(encoding="utf-8")

    # Extract frontmatter
    meta = {}
    if raw.startswith("---"):
        _, fm, content = raw.split("---", 2)
        meta = yaml.safe_load(fm)
        md = content.strip()
    else:
        md = raw

    html = markdown(md)
    slug = meta.get("slug", slugify(meta.get("title", Path(path).stem)))
    post_type = meta.get("type", "post")

    # Prepare post payload
    data = {
        "title": meta.get("title", Path(path).stem),
        "slug": slug,
        "content": html,
        "status": meta.get("status", "draft"),
    }

    # Categories
    if "categories" in meta:
        cat_ids = [wp_get_or_create_term(c, "categories") for c in meta["categories"]]
        data["categories"] = cat_ids

    # Tags
    if "tags" in meta:
        tag_ids = [wp_get_or_create_term(t, "tags") for t in meta["tags"]]
        data["tags"] = tag_ids

    # Featured image
    if "featured_image" in meta:
        img_path = f"content/images/{meta['featured_image']}"
        data["featured_media"] = wp_upload_media(img_path)

    # Check if post exists (by slug)
    existing = wp_get(f"{post_type}?slug={slug}")
    if existing:
        post_id = existing[0]["id"]
        print(f"Updating existing {post_type}: {slug}")
        wp_put(f"{post_type}/{post_id}", data)
    else:
        print(f"Creating new {post_type}: {slug}")
        wp_post(post_type, data)


# --------------------------
# Main Runner
# --------------------------

def main():
    for md_file in Path("content").rglob("*.md"):
        print(f"Processing: {md_file}")
        process_md_file(md_file)

if __name__ == "__main__":
    main()
