import re

def slugify(name: str) -> str:
    # lowercase
    slug = name.lower()

    # remove non-alphanumeric characters
    slug = re.sub(r"[^a-z0-9]", "", slug)

    return slug
