import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts import list_users

if __name__ == '__main__':
    list_users.main()
