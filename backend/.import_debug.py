import sys
sys.path.append(r'C:\Users\user\Desktop\visiontrader_ai')
print('sys.path set')
try:
    import importlib
    mod = importlib.import_module('backend.database')
    print('backend.database imported', mod)
except Exception as e:
    import traceback
    traceback.print_exc()
try:
    mod2 = importlib.import_module('backend.models')
    print('backend.models imported', mod2)
except Exception as e:
    import traceback
    traceback.print_exc()
