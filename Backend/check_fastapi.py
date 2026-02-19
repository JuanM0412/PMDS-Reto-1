import sys
try:
    from fastapi.middleware.cors import CORSMiddleware
    print("Success: fastapi.middleware.cors found!")
    print(f"Python executable: {sys.executable}")
except ImportError as e:
    print(f"Error: {e}")
    print(f"Python executable: {sys.executable}")
    print(f"sys.path: {sys.path}")
