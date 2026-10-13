"""Run HAR_QTFE.ipynb in the project Python kernel."""
from pathlib import Path
import runpy
import sys
entry = Path(__file__).with_name('execute_notebook.py')
sys.argv = [str(entry), 'HAR_QTFE.ipynb']
runpy.run_path(str(entry), run_name='__main__')
