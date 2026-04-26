from sqlalchemy import text
from app.db.connection import engine
from app.models.base import Base
import app.models.core  # Import to register models with Base.metadata

def init_db():
    print("Initializing database...")
    with engine.begin() as conn:
        # 1. Enable pgvector extension
        print("Enabling pgvector extension...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        
        # 2. Drop existing tables to ensure clean schema (v2)
        print("Dropping existing tables...")
        Base.metadata.drop_all(bind=conn)
        
        # 3. Create all tables
        print("Creating all tables...")
        Base.metadata.create_all(bind=conn)
        
        # 4. Create vector index for similarity search
        # Using ivfflat with lists=50 for small/medium inventory
        print("Creating vector index on locations...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_locations_embedding 
            ON locations 
            USING ivfflat (embedding vector_cosine_ops) 
            WITH (lists = 50);
        """))
        
    print("Database initialization complete.")

if __name__ == "__main__":
    init_db()
