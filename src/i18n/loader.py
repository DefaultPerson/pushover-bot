from pathlib import Path

import yaml

_locales: dict[str, dict[str, str]] = {}


def load_locales() -> None:
    """Load all locale files from locales directory."""
    locales_dir = Path(__file__).parent / "locales"

    for locale_file in locales_dir.glob("*.yaml"):
        lang = locale_file.stem
        with open(locale_file, encoding="utf-8") as f:
            _locales[lang] = yaml.safe_load(f) or {}


def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """Get localized text by key."""
    if not _locales:
        load_locales()

    locale = _locales.get(lang, _locales.get("en", {}))
    text = locale.get(key, key)

    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass

    return text
