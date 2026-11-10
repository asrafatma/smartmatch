import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import mongomock

logger = logging.getLogger(__name__)

class Database:
    _client = None
    _db = None
    _is_mock = False

    @classmethod
    def get_db(cls):
        return cls._db

    @classmethod
    def is_mock(cls):
        return cls._is_mock

    @classmethod
    def init(cls, app):
        mongodb_uri = app.config.get("MONGODB_URI", "").strip()
        db_name = app.config.get("MONGODB_DB_NAME", "smartmatch")
        is_testing = app.config.get("TESTING", False)

        if is_testing or mongodb_uri == "mock" or not mongodb_uri:
            logger.info("Initializing in-memory MongoMock database (offline / testing mode)...")
            cls._client = mongomock.MongoClient()
            cls._db = cls._client[db_name]
            cls._is_mock = True
        else:
            try:
                logger.info("Connecting to MongoDB at URI: %s...", mongodb_uri[:20] + "...")
                client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=3000)
                # Quick ping to verify connectivity
                client.admin.command("ping")
                cls._client = client
                cls._db = client[db_name]
                cls._is_mock = False
                logger.info("Successfully connected to MongoDB Atlas / cluster.")
            except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
                logger.warning(
                    "Could not connect to external MongoDB: %s. Falling back to in-memory MongoMock.",
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

            # Claims indexes
            cls._db.claims.create_index([("report_id", ASCENDING)])
            cls._db.claims.create_index([("claimant_id", ASCENDING)])
            cls._db.claims.create_index([("status", ASCENDING)])

            # AI logs indexes
            cls._db.ai_logs.create_index([("report_id", ASCENDING)])
            cls._db.ai_logs.create_index([("created_at", DESCENDING)])
        except Exception as e:
            logger.warning("Index creation notice: %s", e)

def get_db():
    return Database.get_db()

def init_db(app):
    return Database.init(app)
