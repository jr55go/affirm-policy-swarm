"""
Market Sentiment Agent for the Affirm Policy Swarm.
Responsible for monitoring news and social media for market sentiment signals.
"""

import time
import uuid
import hashlib
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import json
import feedparser

# Add workspace root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Load swarm jobs utility
from load_swarm_jobs import load_swarm_jobs

# Add affirm-policy-swarm to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "affirm_policy_swarm"))

# Import required modules
from affirm_policy_swarm.agents.base_agent import BaseAgent
from affirm_policy_swarm.tools.sentiment_tool import analyze_sentiment

from infrastructure.config import load_config
from infrastructure.database import neo4j_session


class MarketSentimentAgent(BaseAgent):
    SWARM_ID = "affirm_policy_swarm"
    PROJECT_SCOPE = "affirm_bnpl_policy"
    """Market Sentiment Agent for monitoring news and social media."""
    
    def __init__(self, agent_id: str = None):
        super().__init__(agent_id or f"market-sent-{str(uuid.uuid4())[:8]}", "Market Sentiment Agent")
        self.SWARM_ID = self.__class__.SWARM_ID
        self.PROJECT_SCOPE = self.__class__.PROJECT_SCOPE
        self.config = load_config()
        # Target keywords for filtering content
        self.target_keywords = ['Affirm', 'BNPL', 'consumer credit', 'Buy Now, Pay Later', 'point of sale lending']
        
    def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute market sentiment monitoring tasks."""
        task_type = task_data.get("type", "unknown")
        
        self.log_thought(f"Market Sentiment agent received task: {task_type}")
        
        if task_type == "monitor_market_sentiment":
            return self._monitor_market_sentiment(task_data)
        else:
            return {
                "status": "error",
                "message": f"Unknown task type: {task_type}",
                "agent_id": self.agent_id
            }
            
    def _monitor_market_sentiment(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor news and social media for market sentiment signals."""
        lookback_hours = task_data.get("lookback_hours", 24)
        sources = task_data.get("sources", None)  # If None, load from config
        
        self.log_thought(f"Monitoring market sentiment (last {lookback_hours}h)")
        
        # CRITICAL INSTRUCTION - DEDUPLICATION: Check if we've recently monitored
        lookup_key = f"market_sentiment:{lookback_hours}"
        recent_monitoring = self.check_redis_deduplication(lookup_key)
        if recent_monitoring:
            self.log_thought(f"Recent market sentiment monitoring found for {lookup_key}, checking for updates")
            # Check if there's been significant change since last monitoring
            last_run = recent_monitoring.get("completed_at")
            if last_run:
                try:
                    last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                    hours_since = (datetime.now(timezone.utc) - last_run_dt).total_seconds() / 3600
                    
                    if hours_since < 1:  # Less than 1 hour since last check (news/social moves faster)
                        self.log_thought(f"Recent check was {hours_since:.1f}h ago, returning cached result")
                        return {
                            "status": "cached",
                            "agent_id": self.agent_id,
                            "data_source": "cache",
                            "cached_result": recent_monitoring,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                except Exception as e:
                    self.log_thought(f"Error parsing timestamp: {e}")
        
        # Load sources dynamically from config if not provided
        if sources is None:
            sources = self._load_market_sources_from_config()
        
        # Discover new content from feeds
        new_urls = self._discover_daily_content(sources, lookback_hours)
        
        # Fetch and analyze content from URLs
        analyzed_content = self._fetch_and_analyze_content(new_urls)
        
        # Store results in graph database
        self._store_regulatory_results("market", "sentiment", analyzed_content)
        
        # Store monitoring result in Redis for deduplication
        monitoring_result = {
            "lookback_hours": lookback_hours,
            "sources_checked": list(sources.keys()),
            "urls_discovered": len(new_urls),
            "content_analyzed": len(analyzed_content),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "summary": self._generate_market_summary(analyzed_content)
        }
        
        self.store_redis_deduplication(lookup_key, monitoring_result, expire_seconds=3600)  # 1 hour
        
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "lookback_hours": lookback_hours,
            "sources_checked": list(sources.keys()),
            "urls_discovered": len(new_urls),
            "content_analyzed": len(analyzed_content),
            "analyzed_content": analyzed_content[:10],  # Return first 10 for brevity
            "summary": monitoring_result["summary"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    def _load_market_sources_from_config(self) -> Dict[str, Any]:
        """Load market sources from infrastructure/config.py"""
        try:
            # Import the config module
            import infrastructure.config as infra_config
            
            # Get the market_sources dictionary from config
            config_obj = infra_config.load_config()
            market_sources = getattr(config_obj.market_data, 'market_sources', {})
            
            if not market_sources:
                self.log_thought("No market_sources found in config, using defaults")
                return self._get_default_market_sources()
                
            return market_sources
        except Exception as e:
            self.log_thought(f"Error loading market sources from config: {e}, using defaults")
            return self._get_default_market_sources()
            
    def _get_default_market_sources(self) -> Dict[str, Any]:
        """Get default market sources if not configured."""
        return {
            "cfpb_newsroom": {
                "name": "CFPB Newsroom",
                "type": "rss",
                "url": "https://www.consumerfinance.gov/about/newsroom/feed/",
                "enabled": True
            },
            "reuters_finance": {
                "name": "Reuters Finance",
                "type": "rss",
                "url": "http://feeds.reuters.com/reuters/businessNews",
                "enabled": True
            },
            "legiscan_federal": {
                "name": "LegiScan Federal",
                "type": "rss",
                "url": "https://legiscan.com/feeds/search?state=US&text=Affirm",
                "enabled": True
            },
            "legiscan_california": {
                "name": "LegiScan California",
                "type": "rss",
                "url": "https://legiscan.com/feeds/search?state=CA&text=BNPL",
                "enabled": True
            },
            "financial_times": {
                "name": "Financial Times",
                "type": "rss",
                "url": "https://www.ft.com/rss/home/us",
                "enabled": True
            },
            "bloomberg_markets": {
                "name": "Bloomberg Markets",
                "type": "rss",
                "url": "https://feeds.bloomberg.com/markets/news.rss",
                "enabled": True
            },
            "sec_edgar": {
                "name": "SEC EDGAR Filings",
                "type": "rss",
                "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=&company=&dateb=&owner=exclude&start=0&count=40&output=atom",
                "enabled": True
            },
            "fed_speeches": {
                "name": "Federal Reserve Speeches",
                "type": "rss",
                "url": "https://www.federalreserve.gov/feeds/press_all.xml",
                "enabled": True
            }
        }
        
    def _discover_daily_content(self, sources: Dict[str, Any], lookback_hours: int) -> List[Dict[str, Any]]:
        """
        Parse dynamically loaded feeds to find new URLs published in the last 24 hours
        containing keywords like 'Affirm', 'BNPL', or 'consumer credit'.
        """
        self.log_thought(f"Discovering daily content from {len([s for s in sources.values() if s.get('enabled', False)])} enabled sources")
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        new_urls = []
        
        for source_key, source_config in sources.items():
            if not source_config.get('enabled', False):
                continue
                
            source_name = source_config.get('name', source_key)
            source_type = source_config.get('type', '')
            source_url = source_config.get('url', '')
            
            self.log_thought(f"Checking source: {source_name} ({source_url})")
            
            try:
                if source_type == 'rss':
                    feed = feedparser.parse(source_url)
                    
                    for entry in feed.entries:
                        # Get published date
                        published = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                        
                        # Skip if older than cutoff
                        if published and published < cutoff_time:
                            continue
                            
                        # Check if content contains target keywords
                        title = getattr(entry, 'title', '')
                        summary = getattr(entry, 'summary', '')
                        content_to_check = f"{title} {summary}".lower()
                        
                        # Check for target keywords
                        keyword_found = False
                        for keyword in self.target_keywords:
                            if keyword.lower() in content_to_check:
                                keyword_found = True
                                break
                                
                        if keyword_found:
                            url = getattr(entry, 'link', '')
                            if url:
                                new_urls.append({
                                    'url': url,
                                    'title': title,
                                    'published': published.isoformat() if published else None,
                                    'source': source_name,
                                    'source_type': source_type
                                })
                                
                # Add support for other source types (API, web scraping) here if needed
                
            except Exception as e:
                self.log_thought(f"Error parsing source {source_name}: {e}")
                continue
                
        # Remove duplicates based on URL
        seen_urls = set()
        unique_urls = []
        for item in new_urls:
            url = item['url']
            if url not in seen_urls:
                seen_urls.add(url)
                unique_urls.append(item)
                
        self.log_thought(f"Discovered {len(unique_urls)} new URLs containing target keywords")
        return unique_urls
        
    def _fetch_and_analyze_content(self, url_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fetch content from URLs and analyze sentiment."""
        self.log_thought(f"Fetching and analyzing content from {len(url_items)} URLs")
        
        analyzed_content = []
        
        for item in url_items:
            url = item['url']
            self.log_thought(f"Fetching content from: {url}")
            
            try:
                # Use the browse_url method from BaseAgent (which uses Playwright)
                content = self.browse_url(url)
                
                if content.startswith("Error:"):
                    self.log_thought(f"Failed to fetch content from {url}: {content}")
                    continue
                    
                # Perform sentiment analysis on the extracted text
                sentiment_score = analyze_sentiment(content)
                
                # Determine if content is relevant based on sentiment strength
                is_relevant = abs(sentiment_score) > 0.1  # Threshold for relevance
                
                analysis = {
                    "content_id": hashlib.md5(url.encode()).hexdigest()[:12],
                    "url": url,
                    "title": item['title'],
                    "published": item['published'],
                    "source": item['source'],
                    "source_type": item['source_type'],
                    "content_length": len(content),
                    "sentiment_score": sentiment_score,
                    "is_relevant": is_relevant,
                    "key_phrases": self._extract_key_phrases(content),
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                    "analyst_agent": self.agent_id
                }
                
                analyzed_content.append(analysis)
                self.log_thought(f"Analyzed content from {url}: sentiment={sentiment_score:.3f}")
                
            except Exception as e:
                self.log_thought(f"Error analyzing content from {url}: {e}")
                continue
                
        # Sort by sentiment score absolute value (most extreme first)
        analyzed_content.sort(key=lambda x: abs(x["sentiment_score"]), reverse=True)
        return analyzed_content
        
    def _extract_key_phrases(self, content: str) -> List[str]:
        """Extract key phrases from content related to our target keywords."""
        # Simple extraction - in production would use NLP
        key_phrases = []
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if any(keyword.lower() in sentence.lower() for keyword in self.target_keywords):
                # Limit length
                if len(sentence) > 200:
                    sentence = sentence[:200] + "..."
                key_phrases.append(sentence)
                
        return key_phrases[:5]  # Return top 5 phrases
        
    def _store_regulatory_results(self, jurisdiction: str, product: str, 
                                analyzed_items: List[Dict[str, Any]]) -> bool:
        """Store market sentiment results in Neo4j graph as 'News' or 'Social' nodes."""
        if not self.neo4j_driver:
            self.logger.warning("Neo4j driver not available for storing results")
            return False
            
        try:
            with neo4j_session() as session:
                # Store each analyzed item as a News or Social node
                for item in analyzed_items:
                    # Determine node type based on source
                    node_type = "News"  # Default
                    if "social" in item['source'].lower() or "twitter" in item['source'].lower() or "reddit" in item['source'].lower():
                        node_type = "Social"
                    
                    # Create or update the sentiment node
                    query = f"""
                    MERGE (n:{node_type} {{
                        content_id: $content_id,
                        url: $url,
                        swarm_id: $swarm_id,
                        project_scope: $project_scope
                    }})
                    SET n.title = $title,
                        n.published = $published,
                        n.source = $source,
                        n.source_type = $source_type,
                        n.content_length = $content_length,
                        n.sentiment_score = $sentiment_score,
                        n.is_relevant = $is_relevant,
                        n.key_phrases = $key_phrases,
                        n.analysis_timestamp = $analysis_timestamp,
                        n.analyst_agent = $analyst_agent,
                        n.updated_at = $updated_at
                    RETURN n.node_id as node_id
                    """
                    
                    result = session.run(query, 
                                       content_id=item['content_id'],
                                       url=item['url'],
                                       title=item['title'],
                                       published=item['published'],
                                       source=item['source'],
                                       source_type=item['source_type'],
                                       content_length=item['content_length'],
                                       sentiment_score=item['sentiment_score'],
                                       is_relevant=item['is_relevant'],
                                       swarm_id=swarm_id,
                                       project_scope=project_scope,
                                       key_phrases=json.dumps(item['key_phrases']),
                                       analysis_timestamp=item['analysis_timestamp'],
                                       analyst_agent=item['analyst_agent'],
                                       updated_at=datetime.now(timezone.utc).isoformat())
                    
                    record = result.single()
                    
                    # Connect to Affirm target node if it exists
                    if record:
                        connect_query = """
                        MATCH (n {node_id: $node_id})
                        MATCH (affirm:Target {name: 'Affirm'})
                        WHERE affirm.node_id IS NOT NULL
                        MERGE (n)-[r:MENTIONS]->(affirm)
                        SET r.relationship_type = 'market_sentiment',
                            r.created_at = $timestamp
                        """
                        session.run(connect_query, node_id=record['node_id'], 
                                  timestamp=datetime.now(timezone.utc).isoformat())
                
                self.logger.debug(f"Stored {len(analyzed_items)} market sentiment items in Neo4j")
                return True
        except Exception as e:
            self.logger.error(f"Error storing market sentiment results: {e}")
            return False
            
    def _generate_market_summary(self, analyzed_items: List[Dict[str, Any]]) -> str:
        """Generate a human-readable summary of market sentiment monitoring results."""
        if not analyzed_items:
            return "No market sentiment content detected containing target keywords"
            
        relevant_count = sum(1 for item in analyzed_items if item.get("is_relevant"))
        news_count = sum(1 for item in analyzed_items if item.get("source_type") == "rss" and "news" in item.get("source", "").lower())
        social_count = len(analyzed_items) - news_count  # Simplified
        
        # Sentiment distribution
        positive_count = sum(1 for item in analyzed_items if item.get("sentiment_score", 0) > 0.1)
        negative_count = sum(1 for item in analyzed_items if item.get("sentiment_score", 0) < -0.1)
        neutral_count = len(analyzed_items) - positive_count - negative_count
        
        summary_parts = []
        if relevant_count > 0:
            summary_parts.append(f"{relevant_count} relevant items")
        if news_count > 0:
            summary_parts.append(f"{news_count} news items")
        if social_count > 0:
            summary_parts.append(f"{social_count} social media items")
            
        sentiment_parts = []
        if positive_count > 0:
            sentiment_parts.append(f"{positive_count} positive")
        if negative_count > 0:
            sentiment_parts.append(f"{negative_count} negative")
        if neutral_count > 0:
            sentiment_parts.append(f"{neutral_count} neutral")
            
        summary = f"Market sentiment monitoring found: {', '.join(summary_parts)}"
        if sentiment_parts:
            summary += f" ({', '.join(sentiment_parts)} sentiment)"
            
        return summary
        
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this agent provides."""
        return [
            "market_sentiment_monitoring",
            "rss_feed_parsing",
            "content_discovery",
            "sentiment_analysis",
            "keyword_filtering",
            "news_social_media_monitoring",
            "affirm_mention_tracking",
            "graph_database_storage",
            "deduplication_enforcement",
            "real_time_alerting"
        ]


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    agent = MarketSentimentAgent()
    
    # Test market sentiment monitoring
    result = agent.execute_task({
        "type": "monitor_market_sentiment",
        "lookback_hours": 24
    })
    
    print("Market sentiment monitoring result:")
    print(f"Status: {result['status']}")
    print(f"Lookback hours: {result.get('lookback_hours')}")
    print(f"URLs discovered: {result.get('urls_discovered')}")
    print(f"Content analyzed: {result.get('content_analyzed')}")
    print(f"Summary: {result.get('summary')}")