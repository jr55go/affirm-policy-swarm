"""
Database connection pooling and management for the Affirm Policy Swarm.
Handles Neo4j and Redis connections with proper pooling and error handling.
"""

import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
import time

# Neo4j imports
try:
    from neo4j import GraphDatabase, Driver, Session, Transaction
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logging.warning("Neo4j driver not available. Install with: pip install neo4j")

# Redis imports
try:
    import redis
    from redis.connection import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available. Install with: pip install redis")

from .config import Neo4jConfig, RedisConfig, load_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and connection pooling."""
    
    def __init__(self, config: Optional[Any] = None):
        self.config = config or load_config()
        self._neo4j_driver: Optional[Driver] = None
        self._redis_pool: Optional[ConnectionPool] = None
        self._redis_client: Optional[redis.Redis] = None
        
    def initialize(self):
        """Initialize all database connections."""
        self._initialize_neo4j()
        self._initialize_redis()
        logger.info("Database connections initialized")
        
    def _initialize_neo4j(self):
        """Initialize Neo4j driver with connection pooling."""
        if not NEO4J_AVAILABLE:
            logger.error("Cannot initialize Neo4j: driver not available")
            return
            
        try:
            self._neo4j_driver = GraphDatabase.driver(
                self.config.neo4j.uri,
                auth=(self.config.neo4j.username, self.config.neo4j.password),
                max_connection_lifetime=self.config.neo4j.max_connection_lifetime,
                max_connection_pool_size=self.config.neo4j.max_connection_pool_size,
                connection_acquisition_timeout=self.config.neo4j.connection_acquisition_timeout
            )
            # Verify connection
            with self._neo4j_driver.session() as session:
                session.run("RETURN 1")
            logger.info("Neo4j connection established")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j connection: {e}")
            self._neo4j_driver = None
            
    def _initialize_redis(self):
        """Initialize Redis connection pool."""
        if not REDIS_AVAILABLE:
            logger.error("Cannot initialize Redis: package not available")
            return
            
        try:
            self._redis_pool = ConnectionPool(
                host=self.config.redis.host,
                port=self.config.redis.port,
                password=self.config.redis.password,
                db=self.config.redis.database,
                socket_timeout=self.config.redis.socket_timeout,
                socket_connect_timeout=self.config.redis.socket_connect_timeout,
                retry_on_timeout=self.config.redis.retry_on_timeout,
                health_check_interval=self.config.redis.health_check_interval,
                max_connections=self.config.redis.connection_pool_size
            )
            self._redis_client = redis.Redis(connection_pool=self._redis_pool)
            # Verify connection
            self._redis_client.ping()
            logger.info("Redis connection pool established")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            self._redis_pool = None
            self._redis_client = None
            
    @property
    def neo4j_driver(self) -> Optional[Driver]:
        """Get Neo4j driver instance."""
        return self._neo4j_driver
        
    @property
    def redis_client(self) -> Optional[redis.Redis]:
        """Get Redis client instance."""
        return self._redis_client
        
    @contextmanager
    def neo4j_session(self):
        """Context manager for Neo4j sessions."""
        if not self._neo4j_driver:
            raise RuntimeError("Neo4j driver not initialized")
            
        session = self._neo4j_driver.session()
        try:
            yield session
        finally:
            session.close()
            
    @contextmanager
    def neo4j_transaction(self):
        """Context manager for Neo4j transactions."""
        with self.neo4j_session() as session:
            tx = session.begin_transaction()
            try:
                yield tx
                tx.commit()
            except Exception:
                tx.rollback()
                raise
                
    def close(self):
        """Close all database connections."""
        if self._neo4j_driver:
            self._neo4j_driver.close()
            self._neo4j_driver = None
            
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None
            
        if self._redis_pool:
            self._redis_pool.disconnect()
            self._redis_pool = None
            
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    return db_manager


# Convenience functions for direct access
def get_neo4j_driver() -> Optional[Driver]:
    """Get Neo4j driver instance."""
    return db_manager.neo4j_driver


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client instance."""
    return db_manager.redis_client


@contextmanager
def neo4j_session():
    """Context manager for Neo4j sessions using global manager."""
    with db_manager.neo4j_session() as session:
        yield session


@contextmanager
def neo4j_transaction():
    """Context manager for Neo4j transactions using global manager."""
    with db_manager.neo4j_transaction() as tx:
        yield tx


if __name__ == "__main__":
    # Test database connections
    logging.basicConfig(level=logging.INFO)
    
    manager = DatabaseManager()
    try:
        manager.initialize()
        
        # Test Neo4j
        if manager.neo4j_driver:
            with manager.neo4j_session() as session:
                result = session.run("RETURN 'Neo4j connection OK' as message")
                print(result.single()["message"])
        
        # Test Redis
        if manager.redis_client:
            manager.redis_client.set("test_key", "test_value", ex=10)
            value = manager.redis_client.get("test_key")
            print(f"Redis test: {value.decode() if value else 'None'}")
            
    finally:
        manager.close()