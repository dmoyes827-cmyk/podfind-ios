import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/testflight-deploy.yml"
REQUIRED = (
    "XCODE_PROJECT",
    "XCODE_SCHEME",
    "APP_BUNDLE_ID",
    "APPLE_TEAM_ID",
    "CERTIFICATE_BASE64",
    "CERTIFICATE_PASSWORD",
    "PROFILE_BASE64",
    "API_KEY_BASE64",
    "API_KEY_ID",
    "API_ISSUER_ID",
)


def deployment_script():
    workflow = WORKFLOW.read_text()
    _, marker, script = workflow.partition("        run: |\n")
    if not marker:
        raise ValueError("TestFlight deployment script not found")
    lines = []
    for line in script.splitlines():
        if line and not line.startswith("          "):
            break
        lines.append(line)
    return textwrap.dedent("\n".join(lines))


class TestFlightValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        project = Path(self.temporary_directory.name) / "App.xcodeproj"
        project.mkdir()
        self.environment = {
            "PATH": os.defpath,
            "RUNNER_TEMP": self.temporary_directory.name,
            "XCODE_PROJECT": str(project),
            "XCODE_SCHEME": "App",
            "APP_BUNDLE_ID": "com.example.app",
            "APPLE_TEAM_ID": "TEAM123",
            "BUILD_NUMBER_OFFSET": "0",
            "CERTIFICATE_BASE64": "placeholder",
            "CERTIFICATE_PASSWORD": "placeholder",
            "PROFILE_BASE64": "placeholder",
            "API_KEY_BASE64": "placeholder",
            "API_KEY_ID": "KEY123",
            "API_ISSUER_ID": "placeholder",
        }

    def run_deployment(self, environment):
        # Stop at the first operation after validation, before signing or upload.
        script = (
            "mktemp() { echo validation-passed >&2; return 42; }\n"
            + deployment_script()
        )
        return subprocess.run(
            ["bash", "-s"],
            input=script,
            text=True,
            capture_output=True,
            env=environment,
            timeout=10,
        )

    def test_missing_and_empty_required_settings_are_rejected(self):
        for name in REQUIRED:
            for value in (None, ""):
                with self.subTest(name=name, value=value):
                    environment = self.environment.copy()
                    if value is None:
                        environment.pop(name)
                    else:
                        environment[name] = value
                    result = self.run_deployment(environment)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn(f"Missing required variable or secret: {name}", result.stdout)
                    self.assertNotIn("validation-passed", result.stderr)

    def test_project_must_be_an_existing_directory(self):
        for path in (Path(self.temporary_directory.name) / "missing", WORKFLOW):
            with self.subTest(path=path):
                environment = self.environment | {"XCODE_PROJECT": str(path)}
                result = self.run_deployment(environment)
                self.assertEqual(result.returncode, 1)
                self.assertIn("XCODE_PROJECT does not point to an existing .xcodeproj.", result.stdout)
                self.assertNotIn("validation-passed", result.stderr)

    def test_invalid_identifiers_and_offsets_are_rejected(self):
        cases = {
            "APP_BUNDLE_ID": ("com.example/app", "com.example app"),
            "APPLE_TEAM_ID": ("TEAM-123", "TEAM 123"),
            "API_KEY_ID": ("KEY_123", "KEY 123"),
            "BUILD_NUMBER_OFFSET": ("", "-1", "1.5", "1000000", " 1"),
        }
        for name, values in cases.items():
            for value in values:
                with self.subTest(name=name, value=value):
                    environment = self.environment | {name: value}
                    result = self.run_deployment(environment)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn("Invalid bundle ID, team ID, API key ID, or build number offset.", result.stdout)
                    self.assertNotIn("validation-passed", result.stderr)

    def test_valid_offset_boundaries_pass_validation(self):
        for offset in ("0", "000000", "999999"):
            with self.subTest(offset=offset):
                environment = self.environment | {"BUILD_NUMBER_OFFSET": offset}
                result = self.run_deployment(environment)
                self.assertEqual(result.returncode, 42)
                self.assertIn("validation-passed", result.stderr)
                self.assertNotIn("::error::", result.stdout)


if __name__ == "__main__":
    unittest.main()
