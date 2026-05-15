import sys
sys.path.append(r'C:\Users\user\Desktop\visiontrader_ai')

try:
    import importlib
    mod = importlib.import_module('backend.services.ai_core')
    print('imported', mod)
    print('ai_core_service', hasattr(mod, 'ai_core_service'))
except Exception as e:
    import traceback
    traceback.print_exc()
