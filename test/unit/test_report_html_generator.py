from types import SimpleNamespace

from pipa.report.html_generator import generate_html_report


def test_generate_html_report_writes_file(tmp_path, monkeypatch):
    out = tmp_path / "report.html"

    class DummyTemplate:
        def __init__(self):
            self.render_called = False

        def render(self, **kwargs):
            self.render_called = True
            return "<html>ok</html>"

    class DummyEnv:
        def __init__(self):
            self.template = DummyTemplate()
            self.filters = {}

        def get_template(self, name):
            return self.template

    dummy_env = DummyEnv()
    monkeypatch.setattr("pipa.report.html_generator.Environment", lambda **_: dummy_env)
    dummy_md = SimpleNamespace(render=lambda text: text)

    generate_html_report(
        output_path=out,
        md_instance=dummy_md,
        warnings=["w1"],
        plots={"p": "html"},
        tables_json={"t": "[]"},
        decision_tree_html="tree",
        findings_for_tree_html="find",
        static_info_data={},
        static_info_str="info",
        context={},
        audit_html="",
    )

    assert out.exists()
    assert "<html>ok</html>" in out.read_text()
    assert dummy_env.template.render_called
