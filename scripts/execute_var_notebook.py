"""Execute VAR_QTFE.ipynb in a fresh project Python Jupyter kernel and save outputs.

Uses the installed Jupyter client directly; no private Colab settings are needed.
An execution error preserves partial outputs and raises instead of saving success.
"""
import json
import os
from pathlib import Path
from queue import Empty
import sys
import tempfile
import time
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "VAR_QTFE.ipynb"
notebook = json.loads(path.read_text())
notebook['metadata'].pop('validated_execution', None)
for cell in notebook['cells']:
    if cell['cell_type'] == 'code':
        cell['execution_count'] = None
        cell['outputs'] = []
path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + '\n')
runtime = Path(tempfile.mkdtemp(prefix="var-notebook-"))
env = dict(os.environ, IPYTHONDIR=str(runtime / "ipython"), MPLCONFIGDIR=str(runtime / "matplotlib"),
           JUPYTER_RUNTIME_DIR=str(runtime), PYTHONDONTWRITEBYTECODE="1")
os.environ['IPYTHONDIR'] = env['IPYTHONDIR']
from jupyter_client import KernelManager
manager = KernelManager(connection_file=str(runtime / "kernel.json"), kernel_name="python3")
manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
client = None
try:
    manager.start_kernel(cwd=str(ROOT), env=env)
    client = manager.client()
    client.start_channels()
    client.wait_for_ready(timeout=60)
    for i, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        cell["outputs"] = []
        msg_id = client.execute(source, stop_on_error=True)
        deadline = time.monotonic() + 900
        error = None
        while time.monotonic() < deadline:
            try:
                message = client.get_iopub_msg(timeout=1)
            except Empty:
                continue
            if message.get("parent_header", {}).get("msg_id") != msg_id:
                continue
            kind, content = message["msg_type"], message["content"]
            if kind == "execute_input":
                cell["execution_count"] = content["execution_count"]
            elif kind == "stream":
                cell["outputs"].append(dict(output_type="stream", name=content["name"], text=content["text"]))
            elif kind in ["execute_result", "display_data"]:
                output = dict(output_type=kind, data=content["data"], metadata=content.get("metadata", {}))
                if kind == "execute_result":
                    output["execution_count"] = content["execution_count"]
                cell["outputs"].append(output)
            elif kind == "error":
                error = content
                cell["outputs"].append(dict(output_type="error", ename=content["ename"], evalue=content["evalue"], traceback=content["traceback"]))
            elif kind == "status" and content["execution_state"] == "idle":
                break
        else:
            raise TimeoutError(f"Notebook cell {i} exceeded 900 seconds")
        path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n")
        if error:
            raise RuntimeError(f"Cell {i}: {error['ename']}: {error['evalue']}")
        print(f"Executed cell {i}: {len(cell['outputs'])} saved outputs", flush=True)
    notebook["metadata"].setdefault("language_info", {})["version"] = sys.version.split()[0]
    notebook["metadata"]["kernelspec"]["display_name"] = "Python 3 (project .venv)"
    notebook["metadata"]["validated_execution"] = {"python": sys.version.split()[0], "errors": 0,
        "executed_at": datetime.now(ZoneInfo('Europe/Amsterdam')).isoformat(), "method": "fresh Jupyter kernel; all code cells in order"}
    path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n")
    print(f"Saved executed notebook: {path}", flush=True)
finally:
    if client:
        client.stop_channels()
    if manager.has_kernel:
        manager.shutdown_kernel(now=True)
