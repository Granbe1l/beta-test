from pathlib import Path
import ast
import pytest
ROOT=Path(__file__).resolve().parents[1]


def test_no_production_secrets_committed():
    gitignore=(ROOT/'.gitignore').read_text()
    assert '.env\n' in gitignore and '.streamlit/secrets.toml' in gitignore
    assert not (ROOT/'.env').exists() and not (ROOT/'.streamlit/secrets.toml').exists()
    assert 'PASSWORD@HOST' in (ROOT/'.streamlit/secrets.example.toml').read_text() # placeholder only


def test_no_write_git_api():
    source=(ROOT/'src/collectors/client.py').read_text()
    assert 'self.session.get(' in source
    for write in ('self.session.post(', 'self.session.patch(', 'self.session.delete(', 'self.session.put('):
        assert write not in source


def test_responsive_styles_and_empty_states():
    css=(ROOT/'src/ui/theme.py').read_text()
    pages=(ROOT/'src/ui/pages.py').read_text()
    assert '@media(max-width:700px)' in css
    assert 'No verified data' in css
    assert 'Insufficient Data' in pages
    assert 'Repository Explorer' in (ROOT/'streamlit_app.py').read_text()


def test_all_python_parses():
    for file in list((ROOT/'src').rglob('*.py'))+list((ROOT/'scripts').glob('*.py'))+[ROOT/'streamlit_app.py']:
        ast.parse(file.read_text(encoding='utf8'),filename=str(file))


def test_streamlit_runtime_smoke_if_installed():
    pytest.importorskip('streamlit')
    from src.ui.pages import fmt_pct,fmt_days
    assert fmt_pct(None)=='Insufficient Data'
    assert fmt_days(2.5)=='2.5 days'
