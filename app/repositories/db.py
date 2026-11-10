import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
import mongomock

logger = logging.getLogger(__name__)

class Database:
    _client = None
    _db = None
    _is_mock = False
    _fallback_reason = None

    @classmethod
    def get_db(cls):
        return cls._db

    @classmethod
    def is_mock(cls):
        return cls._is_mock

    @classmethod
    def fallback_reason(cls):
        """Non-None when a real MongoDB URI was configured but could not be reached."""
        return cls._fallback_reason

    @classmethod
    def ping(cls) -> bool:
        if cls._db is None:
            return False
        if cls._is_mock:
            return True
        try:
            cls._client.admin.command("ping")
            return True
        except Exception:
            return False

    @classmethod
    def init(cls, app):
        mongodb_uri = app.config.get("MONGODB_URI", "").strip()
        db_name = app.config.get("MONGODB_DB_NAME", "smartmatch")
        is_testing = app.config.get("TESTING", False)
        allow_fallback = app.config.get("MONGODB_ALLOW_MOCK_FALLBACK", True)
        cls._fallback_reason = None

        if is_testing or mongodb_uri == "mock" or not mongodb_uri:
            logger.info("Initializing in-memory MongoMock database (offline / testing mode)...")
            cls._client = mongomock.MongoClient()
            cls._db = cls._client[db_name]
            cls._is_mock = True
        else:
            try:
                # Never log credentials: only log the scheme
                logger.info("Connecting to MongoDB (%s://...)", mongodb_uri.split("://", 1)[0])
                client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=3000)
                # Quick ping to verify connectivity
                client.admin.command("ping")
                cls._client = client
                cls._db = client[db_name]
                cls._is_mock = False
                logger.info("Successfully connected to MongoDB Atlas / cluster.")
            except Exception as e:
                if not allow_fallback:
                    raise RuntimeError(
                        f"Could not connect to MongoDB and MONGODB_ALLOW_MOCK_FALLBACK is disabled: {e}"
                    ) from e
                cls._fallback_reason = type(e).__name__
                logger.error(
                    "Could not connect to external MongoDB: %s. Falling back to in-memory MongoMock "
                    "(DATA WILL NOT BE PERSISTED).",
                    e,
                )
                cls._client = mongomock.MongoClient()
                cls._db = cls._client[db_name]
                cls._is_mock = True

        cls._ensure_indexes()
        return cls._db

    @classmethod
    def _ensure_indexes(cls):
        try:
            # Users indexes
            cls._db.users.create_index([("email", ASCENDING)], unique=True)
            cls._db.users.create_index([("role", ASCENDING)])

            # Reports indexes
            cls._db.reports.create_index([("report_type", ASCENDING)])
            cls._db.reports.create_index([("status", ASCENDING)])
            cls._db.reports.create_index([("user_id", ASCENDING)])
            cls._db.reports.create_index([("incident_date", DESCENDING)])
            cls._db.reports.create_index([("created_at", DESCENDING)])

            # Matches indexes
            cls._db.matches.create_index([("lost_report_id", ASCENDING)])
            cls._db.matches.create_index([("found_report_id", ASCENDING)])
            cls._db.matches.create_index([("score", DESCENDING)])
            cls._db.matches.create_index(
                [("lost_report_id", ASCENDING), ("found_report_id", ASCENDING)], unique=True
            )

            # Claims indexes
            cls._db.claims.create_index([("report_id", ASCENDING)])
            cls._db.claims.create_index([("claimant_id", ASCENDING)])
            cls._db.claims.create_index([("status", ASCENDING)])
            # One claim per user per item: a new claim cannot bypass the attempt limit
            cls._db.claims.create_index(
                [("report_id", ASCENDING), ("claimant_id", ASCENDING)], unique=True
            )
            cls._db.verification_clues.create_index([("report_id", ASCENDING)], unique=True)
            cls._db.reports.create_index(
                [("report_type", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)]
            )

            # AI logs indexes
            cls._db.ai_logs.create_index([("report_id", ASCENDING)])
            cls._db.ai_logs.create_index([("created_at", DESCENDING)])
        except Exception as e:
            logger.warning("Index creation notice: %s", e)

def get_db():
    return Database.get_db()

def init_db(app):
    return Database.init(app)
