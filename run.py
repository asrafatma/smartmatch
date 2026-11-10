import os
from app import create_app
from app.repositories.user_repository import UserRepository
from scripts.seed_database import seed

app = create_app()

def ensure_initial_seed():
    """Auto-seeds demo accounts if running in development with an empty database."""
    with app.app_context():
        try:
            if UserRepository.count() == 0:
                print("Notice: Empty database detected. Running initial seed with demo accounts...")
                seed()
        except Exception as e:
            print(f"Notice during initial seed check: {e}")

if __name__ == "__main__":
    ensure_initial_seed()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    print(f"\n=======================================================")
    print(f"  SmartMatch Campus Platform Server")
    print(f"  Local URL: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
