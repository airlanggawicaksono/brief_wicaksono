import base64
import csv
import json
import os
import subprocess
import sys
import tempfile
import textwrap

from langchain_core.tools import tool

from app.repository.workspace import WorkspaceRepository


def _write_csv(path: str, rows: list[dict]) -> None:
    if not rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write("")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def create_run_python_tool(workspace_repo: WorkspaceRepository, session_id: str):
    @tool
    def run_python(code: str) -> dict:
        """Run Python code to generate a chart or analyze workspace data.

        Use this when the user asks for a chart, dashboard, or visualization.
        Workspace datasets are written as CSV files before the script runs.
        A dict called `workspace` maps each dataset name to its full CSV file path.
        Always load data using the workspace dict — never use bare filenames:

            import pandas as pd
            df = pd.read_csv(workspace['analytics'])   # correct
            # df = pd.read_csv('analytics.csv')        # wrong — will fail

        To produce an image, save to 'output.png':

            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            ax.bar(df['name'], df['total'])
            plt.tight_layout()
            plt.savefig('output.png')

        Do not call plt.show(). The saved image is returned as base64.
        Text printed to stdout is returned when no image is produced.
        """
        names = workspace_repo.list(session_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            # write each dataset to a CSV file in tmpdir
            file_map: dict[str, str] = {}
            for name in names:
                rows = workspace_repo.load(session_id, name)
                if rows is not None:
                    csv_path = os.path.join(tmpdir, f"{name}.csv")
                    _write_csv(csv_path, rows)
                    file_map[name] = csv_path

            output_path = os.path.join(tmpdir, "output.png")

            # build script by joining parts — never use textwrap.dedent on f-strings
            # that embed multi-line user code (dedent sees mixed indentation and breaks)
            boilerplate = "\n".join([
                "import matplotlib",
                "matplotlib.use('Agg')",
                "import matplotlib.pyplot as plt",
                "",
                f"workspace = {json.dumps(file_map)}",
                f"_output_path = {repr(output_path)}",
                "",
            ])
            # normalise user code indentation and rewrite savefig path
            user_code = textwrap.dedent(code)
            user_code = user_code.replace("savefig('output.png')", "savefig(_output_path)")
            user_code = user_code.replace('savefig("output.png")', "savefig(_output_path)")
            script = boilerplate + user_code

            script_path = os.path.join(tmpdir, "script.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script)

            try:
                proc = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=tmpdir,
                )
            except subprocess.TimeoutExpired:
                return {"error": {"code": "timeout", "message": "Script timed out after 30 seconds."}}

            if proc.returncode != 0:
                return {"error": {"code": "execution_error", "message": proc.stderr[-800:].strip()}}

            if os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    image_b64 = base64.b64encode(f.read()).decode()
                return {"image": image_b64, "format": "png"}

            return {"output": proc.stdout.strip() or "Script ran with no output."}

    return run_python
