"""O ponto de entrada do site deve permanecer estático e acessível."""
from pathlib import Path


def test_home_page_exists_and_links_to_study():
    page = Path("index.html")
    assert page.is_file()
    text = page.read_text(encoding="utf-8")
    assert 'lang="pt-BR"' in text
    assert 'href="./PAGINA.html"' in text
    assert Path("PAGINA.html").is_file()


def test_no_install_network_hook():
    import json
    package = json.loads(Path("package.json").read_text(encoding="utf-8"))
    assert "postinstall" not in package.get("scripts", {})
