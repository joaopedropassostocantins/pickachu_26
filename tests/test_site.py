"""Testes para a página pública e a ausência de telemetria de rede."""
import json
from pathlib import Path


def test_home_page_exists_and_links_to_study():
    page = Path("index.html")
    assert page.is_file()
    text = page.read_text(encoding="utf-8")
    assert 'lang="pt-BR"' in text
    assert 'href="./PAGINA.html"' in text
    assert Path("PAGINA.html").is_file()


def test_install_telemetry_is_local_and_opt_in():
    package = json.loads(Path("package.json").read_text(encoding="utf-8"))
    assert package.get("scripts", {}).get("postinstall") == "node scripts/postinstall.js"
    code = Path("lib/telemetry.js").read_text(encoding="utf-8")
    assert "PIKACHU_ANALYZER_TELEMETRY !== '1'" in code
    assert "writeFileSync" in code
    assert "fetch(" not in code
    assert "https://" not in code
