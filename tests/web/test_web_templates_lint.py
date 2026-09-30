"""Regression tests for template cleanliness, Alpine CSP rules, and hx-target DOM integrity."""

import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

TEMPLATES_DIR = Path("app/web/templates")
ALPINE_BARE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_$][\w$.]*$")


def test_alpine_csp_directive_values_are_bare_identifiers() -> None:
    """Verify Alpine directive values across templates match ^[A-Za-z_$][\\w$.]*$."""
    template_files = list(TEMPLATES_DIR.rglob("*.html"))
    assert len(template_files) > 0, "No template files found"

    violations: list[str] = []

    for path in template_files:
        content = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")

        for tag in soup.find_all(True):
            if not isinstance(tag, Tag):
                continue
            for attr_name, attr_val in tag.attrs.items():
                if isinstance(attr_val, list):
                    val_str = " ".join(attr_val).strip()
                else:
                    val_str = str(attr_val or "").strip()

                if not val_str:
                    continue

                is_alpine = (
                    attr_name.startswith("x-on:")
                    or attr_name.startswith("@")
                    or attr_name == "x-show"
                    or attr_name == "x-text"
                    or attr_name.startswith("x-bind:")
                    or attr_name.startswith(":")
                    or attr_name == "x-init"
                    or attr_name == "x-model"
                )

                if is_alpine and not ALPINE_BARE_IDENTIFIER_PATTERN.match(val_str):
                    violations.append(
                        f'{path.name} <{tag.name} {attr_name}="{val_str}">: '
                        f"expression '{val_str}' does not match CSP bare identifier pattern"
                    )

    assert not violations, "Found Alpine CSP directive violations:\n" + "\n".join(violations)


def test_hx_target_ids_exist_in_dom_templates() -> None:
    """Verify every hx-target='#id' attribute refers to an element ID in some template."""
    template_files = list(TEMPLATES_DIR.rglob("*.html"))
    assert len(template_files) > 0, "No template files found"

    defined_ids: set[str] = set()
    targets: list[tuple[Path, str, str]] = []

    for path in template_files:
        content = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")

        for tag in soup.find_all(True):
            if not isinstance(tag, Tag):
                continue

            if "id" in tag.attrs:
                id_val = str(tag.attrs["id"]).strip()
                if id_val:
                    defined_ids.add(id_val)

            if "hx-target" in tag.attrs:
                target_val = str(tag.attrs["hx-target"]).strip()
                if target_val.startswith("#"):
                    target_id = target_val[1:]
                    targets.append((path, tag.name, target_id))

    missing_targets: list[str] = []
    for file_path, tag_name, target_id in targets:
        if target_id not in defined_ids:
            missing_targets.append(
                f'{file_path.name} <{tag_name} hx-target="#{target_id}">: '
                f"target ID '{target_id}' is not defined in any template"
            )

    assert not missing_targets, "Found missing hx-target ID references:\n" + "\n".join(
        missing_targets
    )


def test_every_hx_get_and_post_has_target_and_swap() -> None:
    """Verify every tag with hx-get or hx-post has both hx-target and hx-swap attributes."""
    template_files = list(TEMPLATES_DIR.rglob("*.html"))
    assert len(template_files) > 0, "No template files found"

    missing: list[str] = []
    for path in template_files:
        content = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")

        for tag in soup.find_all(True):
            if not isinstance(tag, Tag):
                continue

            has_hx_verb = "hx-get" in tag.attrs or "hx-post" in tag.attrs
            if has_hx_verb:
                has_target = "hx-target" in tag.attrs
                has_swap = "hx-swap" in tag.attrs
                if not (has_target and has_swap):
                    missing.append(
                        f"{path.name} <{tag.name}> has hx-get/post but missing "
                        f"{'hx-target' if not has_target else ''} "
                        f"{'hx-swap' if not has_swap else ''}".strip()
                    )

    msg = "Found hx-get/post tags missing explicit hx-target or hx-swap:\n" + "\n".join(missing)
    assert not missing, msg


def test_htmx_config_disable_inheritance() -> None:
    """Verify htmx-config meta in base.html contains 'disableInheritance':true."""
    base_path = TEMPLATES_DIR / "base.html"
    content = base_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    meta = soup.find("meta", {"name": "htmx-config"})
    assert meta is not None, "meta[name=htmx-config] not found in base.html"
    meta_content = str(meta.get("content", ""))
    has_disable_inh = (
        '"disableInheritance":true' in meta_content or '"disableInheritance": true' in meta_content
    )
    assert has_disable_inh
