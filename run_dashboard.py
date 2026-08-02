"""Standalone dashboard runner for development/preview."""
import sys
sys.path.insert(0, ".")

from dashboard.app import create_app

app = create_app()
app.run(host="0.0.0.0", port=8050, debug=False)
