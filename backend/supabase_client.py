"""
supabase_client.py
──────────────────
Initialises and exports the Supabase client.
Uses the SERVICE ROLE KEY so we can bypass RLS from the backend.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env file (no-op if running in an environment that already has vars)
load_dotenv()

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_KEY: str = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
