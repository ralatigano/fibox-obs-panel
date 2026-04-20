from src.app import FiboxApp
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


if __name__ == "__main__":
    app = FiboxApp()
    app.mainloop()
