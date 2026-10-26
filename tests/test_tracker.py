import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tracker = load_module("tracker_under_test", "cli/tracker/tracker.py")
study_site = load_module("study_site_under_test", "cli/tracker/study_site.py")


class TrackerTests(unittest.TestCase):
    def test_followup_classifies_template_rows(self):
        original = tracker.CSV_PATH
        try:
            tracker.CSV_PATH = str(ROOT / "SEGUIMIENTO.template.csv")
            rows = tracker.load_rows()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["empresa"], "Acme Cloud Technologies")
        finally:
            tracker.CSV_PATH = original

    def test_validate_rejects_missing_csv_columns(self):
        original = tracker.CSV_PATH
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".csv") as csv_file:
                csv_file.write("empresa,estado\nAcme,Postulado\n")
                csv_file.flush()
                tracker.CSV_PATH = csv_file.name
                with self.assertRaises(ValueError):
                    tracker.load_rows()
        finally:
            tracker.CSV_PATH = original

    def test_study_sanitizer_removes_private_lines(self):
        content = (
            "# Study\n"
            "> Contact: private@example.com\n"
            "- [ ] Safe checklist item\n"
            "Postulación enviada: Example Corp\n"
            "Meeting: https://meet.google.com/example\n"
        )
        sanitized, removed = study_site.sanitize(content)
        self.assertIn("Safe checklist item", sanitized)
        self.assertNotIn("private@example.com", sanitized)
        self.assertGreaterEqual(len(removed), 2)
        self.assertTrue(study_site.LEAK_PATTERNS["enlace de reunión"].search(content))

    def test_report_generation_has_no_personal_banners_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "dashboard.html"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "cli/tracker/tracker.py"),
                    "report",
                    "--out",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            html = output.read_text(encoding="utf-8")
            self.assertNotIn("ALPRO", html)
            self.assertIn('"priorityBanners": []', html)

    def test_study_build_is_reproducible_in_temp_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "cli/tracker/study_site.py"),
                    "--out",
                    temp_dir,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            index = Path(temp_dir) / "index.html"
            self.assertTrue(index.is_file())
            self.assertIn("Plan de estudio", index.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
