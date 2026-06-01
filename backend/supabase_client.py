from typing import Optional

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

from config import settings

SUPABASE_CONFIGURED = bool(
    settings.SUPABASE_URL and settings.SUPABASE_KEY and create_client is not None
)
supabase_client: Optional[Client] = None

if SUPABASE_CONFIGURED:
    try:
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as exc:
        print(f"Supabase client initialization failed: {exc}")
        supabase_client = None
        SUPABASE_CONFIGURED = False
else:
    if create_client is None:
        print("Supabase client package not installed. Install supabase package to use Supabase.")
    else:
        print("Supabase is not configured because SUPABASE_URL or SUPABASE_KEY is missing.")
