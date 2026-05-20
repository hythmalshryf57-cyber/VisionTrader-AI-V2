from main import app
routes = [route.path for route in app.routes if hasattr(route, 'path')]
for route in routes:
    print(route)
print('DONE')
