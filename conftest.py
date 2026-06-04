import os
import sys

root = os.path.abspath(os.path.dirname(__file__))
backend_path = os.path.join(root, 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


def pytest_ignore_collect(path, config):
    path_str = os.path.abspath(str(path))
    scripts_dir = os.path.abspath(os.path.join(root, 'backend', 'scripts'))
    if path_str == scripts_dir or path_str.startswith(scripts_dir + os.sep):
        return True
    return False
