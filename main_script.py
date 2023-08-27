import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from CaptainsLog.main import app

app.run(sys.argv)