"""Source Registry for Affirm Policy Swarm.
Authoritative catalog for all swarm data sources.
"""
import datetime
import os

# Import the new CFPBConnector for Tier 1 migration
try:
    from infrastructure.connectors.regulators.cfpb_connector import CFPBConnector
    CFPB_CONNECTOR_AVAILABLE = True
except ImportError:
    CFPB_CONNECTOR_AVAILABLE = False
    CFPBConnector = None

# Import the new LegiScanConnector for Tier 1 migration
try:
    from infrastructure.connectors.legislation.legiscan_connector import LegiScanConnector
    LEGISCAN_CONNECTOR_AVAILABLE = True
except ImportError:
    LEGISCAN_CONNECTOR_AVAILABLE = False
    LegiScanConnector = None

# Import the new ResearchConnector for Phase 4 implementation
try:
    from infrastructure.connectors.research.research_connector import ResearchConnector
    RESEARCH_CONNECTOR_AVAILABLE = True
except ImportError:
    RESEARCH_CONNECTOR_AVAILABLE = False
    ResearchConnector = None

# Import the new PolicymakerConnector for Phase 5 implementation
try:
    from infrastructure.connectors.policy.policymaker_connector import PolicymakerConnector
    POLICYMAKER_CONNECTOR_AVAILABLE = True
except ImportError:
    POLICYMAKER_CONNECTOR_AVAILABLE = False
    PolicymakerConnector = None

# Import the new NewsConnector for Phase 6 implementation
try:
    from infrastructure.connectors.news.news_connector import NewsConnector
    NEWS_CONNECTOR_AVAILABLE = True
except ImportError:
    NEWS_CONNECTOR_AVAILABLE = False
    NewsConnector = None

# Import the new PublicStatementConnector for Phase 7 implementation
try:
    from infrastructure.connectors.social.public_statement_connector import PublicStatementConnector
    PUBLIC_STATEMENT_CONNECTOR_AVAILABLE = True
except ImportError:
    PUBLIC_STATEMENT_CONNECTOR_AVAILABLE = False
    PublicStatementConnector = None

class SourceRegistry:
    def __init__(self):
        self._catalog = {

            "nclc_advocacy": {
                "source_type": "news", "access_method": "rss",
                "url": "https://www.nclc.org/feed/", "cadence": "daily", "status": "active"
            },
            "brookings_tech": {
                "source_type": "news", "access_method": "rss",
                "url": "https://www.brookings.edu/feed/", "cadence": "daily", "status": "active"
            },
            "troutman_pepper_law": {
                "source_type": "news", "access_method": "rss",
                "url": "https://www.consumerfinancialserviceslawmonitor.com/feed/", "cadence": "daily", "status": "active"
            },
            "payments_dive": {
                "source_type": "news", "access_method": "rss",
                "url": "https://www.paymentsdive.com/feeds/news/", "cadence": "daily", "status": "active"
            },
            "cfpb_newsroom": {
                "source_type": "news", "access_method": "rss",
                "url": "https://www.consumerfinance.gov/about-us/newsroom/feed/", "cadence": "daily", "status": "active"
            },

            "congress_gov": {
                "source_type": "legislation", "access_method": "api",
                "url": "https://api.congress.gov/v3/", "cadence": "daily",
                "enabled": True, "rate_limit": "250/day", "last_success": None, "last_error": None
            },
            "legiscan": {
                "source_type": "legislation", "access_method": "api",
                "url": "https://api.legiscan.com/", "cadence": "daily",
                "enabled": True, "rate_limit": "unlimited", "last_success": None, "last_error": None
            },
            "federal_register": {
                "source_type": "regulator", "access_method": "api",
                "url": "https://www.federalregister.gov/api/v1/", "cadence": "daily",
                "enabled": True, "rate_limit": "polite", "last_success": None, "last_error": None
            },
            "brookings_policy_research": {
                "source_type": "research", "access_method": "scraper",
                "url": "https://www.brookings.edu/research/", "cadence": "weekly",
                "enabled": True, "rate_limit": "polite", "last_success": None, "last_error": None
            },
            "cfpb_enforcement": {
                "source_type": "regulator", "access_method": "api",
                "url": "https://www.consumerfinance.gov/data-research/consumer-complaints/", "cadence": "daily",
                "enabled": True, "rate_limit": "polite", "last_success": None, "last_error": None
            },
            "senate_banking_committee": {
                "source_type": "policymaker", "access_method": "rss",
                # Base URL for the source (used when online)
                "url": "https://www.banking.senate.gov/",
                "cadence": "daily",
                "enabled": True, "rate_limit": "polite", "last_success": None, "last_error": None,
                # Add fallback configuration for robustness
                "fallback_enabled": False,  # DISABLED MOCK DATA
                "fallback_data": [
                    {
                        "title": "Sample Senate Banking Committee Statement (Offline Fallback)",
                        "text_context": "This is fallback data generated when the Senate Banking Committee RSS feed is unavailable. Represents typical committee activity regarding financial regulation oversight.",
                        "source": "Senate Banking Committee [OFFLINE FALLBACK]",
                        "url": "https://www.banking.senate.gov/ (Cached)",
                        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                        "impact_score": "medium"
                    }
                ],
                "error_tolerance": "log_and_continue"
            },
            "fintech_press": {
                "source_type": "news", "access_method": "rss",
                # Updated to a working fintech RSS feed
                "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", 
                "cadence": "daily",
                "enabled": True, "rate_limit": "polite", "last_success": None, "last_error": None
            },
            "cfpb_director_statements": {
                "source_type": "social_public", "access_method": "api",
                "url": "https://api.example.com/cfpb/director/statements", "cadence": "hourly",
                "enabled": True, "rate_limit": "polite", "last_success": None, "last_error": None
            },
            "policymaker_statements": {
                "source_type": "policymaker", "access_method": "rss",
                # Placeholder URL - actual feeds configured in connector
                "url": "https://www.federalreserve.gov/feeds/press_all.xml",
                "cadence": "daily",
                "enabled": True, "rate_limit": "polite", "last_success": None, "last_error": None
            },
            "financial_news": {
                "source_type": "news", "access_method": "rss",
                # Placeholder URL - actual feeds configured in connector
                "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?profile=120000000&id=10000664",
                "cadence": "daily",
                "enabled": True, "rate_limit": "polite", "last_success": None, "last_error": None
            },
            "public_social_statements": {
                "source_type": "social_public", "access_method": "rss",
                # Placeholder URL - actual feeds configured in connector
                "url": "Multiple public statement sources (see connector config)",
                "cadence": "daily",
                "enabled": True, "rate_limit": "polite", "last_success": None, "last_error": None
            }
        }
        
        # Initialize CFPB connector if available (Tier 1 migration)
        if CFPB_CONNECTOR_AVAILABLE:
            cfpb_config = {
                'api_base_url': 'https://data.consumerfinance.gov/resource/s6ew-h6mp.json',
                'timeout': 30,
                'rate_limit_delay': 1.0
            }
            self._cfpb_connector = CFPBConnector(cfpb_config)
        else:
            self._cfpb_connector = None

        # Initialize LegiScan connector if available (Tier 1 migration)
        if LEGISCAN_CONNECTOR_AVAILABLE:
            legiscan_config = {
                'api_base_url': 'https://api.legiscan.com/',
                'timeout': 30,
                'rate_limit_delay': 1.0,
                'api_key': None  # Will be set from environment or config later
            }
            self._legiscan_connector = LegiScanConnector(legiscan_config)
        else:
            self._legiscan_connector = None

        # Initialize Research connector if available (Phase 4 implementation)
        if RESEARCH_CONNECTOR_AVAILABLE:
            research_config = {
                'timeout': 30,
                'rate_limit_delay': 2.0,
                'feeds': {
                    'Brookings Institution': 'https://www.brookings.edu/feed/',
                    'National Consumer Law Center': 'https://www.nclc.org/feed',
                    'Consumer Federation of America': 'https://consumerfed.org/feed/',
                    'New America': 'https://www.newamerica.org/feed/',
                    'Urban Institute': 'https://www.urban.org/feeds/research.xml'
                }
            }
            self._research_connector = ResearchConnector(research_config)
        else:
            self._research_connector = None

        # Initialize Policymaker connector if available (Phase 5 implementation)
        if POLICYMAKER_CONNECTOR_AVAILABLE:
            policymaker_config = {
                'feeds': [
                    # Senate Banking Committee
                    {
                        'name': 'Senate Banking Committee',
                        'url': 'https://www.banking.senate.gov/imo/media/doc/RSSFeed.xml',
                        'source_name_override': 'Senate Banking Committee'
                    },
                    # House Financial Services Committee
                    {
                        'name': 'House Financial Services Committee',
                        'url': 'https://financialservices.house.gov/news/rss.aspx',
                        'source_name_override': 'House Financial Services Committee'
                    },
                    # Senate Finance Committee
                    {
                        'name': 'Senate Finance Committee',
                        'url': 'https://www.finance.senate.gov/feed/',
                        'source_name_override': 'Senate Finance Committee'
                    },
                    # House Ways and Means Committee
                    {
                        'name': 'House Ways and Means Committee',
                        'url': 'https://waysandmeans.house.gov/news/rss.aspx',
                        'source_name_override': 'House Ways and Means Committee'
                    },
                    # Senator Elizabeth Warren
                    {
                        'name': 'Senator Elizabeth Warren',
                        'url': 'https://www.warren.senate.gov/rss/',
                        'source_name_override': 'Office of Sen. Elizabeth Warren'
                    },
                    # Senator Sherrod Brown
                    {
                        'name': 'Senator Sherrod Brown',
                        'url': 'https://www.brown.senate.gov/rss/',
                        'source_name_override': 'Office of Sen. Sherrod Brown'
                    },
                    # Senator Mike Crapo
                    {
                        'name': 'Senator Mike Crapo',
                        'url': 'https://www.crapo.senate.gov/rss/',
                        'source_name_override': 'Office of Sen. Mike Crapo'
                    },
                    # Senator Pat Toomey
                    {
                        'name': 'Senator Pat Toomey',
                        'url': 'https://www.toomey.senate.gov/rss/',
                        'source_name_override': 'Office of Sen. Pat Toomey'
                    },
                    # Federal Reserve Chair (press releases)
                    {
                        'name': 'Federal Reserve Press Releases',
                        'url': 'https://www.federalreserve.gov/feeds/press_all.xml',
                        'source_name_override': 'Federal Reserve Board'
                    },
                    # CFPB Director
                    {
                        'name': 'CFPB Director Newsroom',
                        'url': 'https://www.consumerfinance.gov/about-us/newsroom/rss/',
                        'source_name_override': 'Consumer Financial Protection Bureau'
                    }
                ],
                'timeout': 30,
                'rate_limit_delay': 1.0
            }
            self._policymaker_connector = PolicymakerConnector(policymaker_config)
        else:
            self._policymaker_connector = None

        # Initialize News connector if available (Phase 6 implementation)
        if NEWS_CONNECTOR_AVAILABLE:
            news_config = {
                'feeds': [
                    # Reuters Financial News
                    {
                        'name': 'Reuters Financial News',
                        'url': 'http://feeds.reuters.com/reuters/businessNews',
                        'source_name_override': 'Reuters'
                    },
                    # American Banker
                    {
                        'name': 'American Banker',
                        'url': 'https://www.americanbanker.com/rss',
                        'source_name_override': 'American Banker'
                    },
                    # Politico Pro Financial Services
                    {
                        'name': 'Politico Pro Financial Services',
                        'url': 'https://www.politico.com/rss/politicoprofinancialservices.xml',
                        'source_name_override': 'Politico Pro'
                    },
                    # Bloomberg Finance
                    {
                        'name': 'Bloomberg Finance',
                        'url': 'https://feeds.bloomberg.com/markets/news.rss',
                        'source_name_override': 'Bloomberg'
                    },
                    # Wall Street Journal - Markets
                    {
                        'name': 'Wall Street Journal - Markets',
                        'url': 'https://feeds.wsj.com/public/rss/marketsnews',
                        'source_name_override': 'Wall Street Journal'
                    }
                ],
                'timeout': 30,
                'rate_limit_delay': 1.0
            }
            self._news_connector = NewsConnector(news_config)
        else:
            self._news_connector = None

        # Initialize Public Statement connector if available (Phase 7 implementation)
        if PUBLIC_STATEMENT_CONNECTOR_AVAILABLE:
            public_statement_config = {
                'feeds': [
                    # Federal Reserve Chair (Jerome Powell) - Speeches
                    {
                        'name': 'Federal Reserve Chair Speeches',
                        'url': 'https://www.federalreserve.gov/feeds/press_speech.xml',
                        'source_name_override': 'Federal Reserve Chair'
                    },
                    # Treasury Secretary Press Releases
                    {
                        'name': 'Treasury Department Press Releases',
                        'url': 'https://home.treasury.gov/news/press-releases/rss',
                        'source_name_override': 'U.S. Department of the Treasury'
                    },
                    # SEC Chairman Statements
                    {
                        'name': 'SEC Chairman Statements',
                        'url': 'https://www.sec.gov/news/pressreleases.rss',
                        'source_name_override': 'Securities and Exchange Commission'
                    },
                    # FDIC Chairman Statements
                    {
                        'name': 'FDIC Chairman Statements',
                        'url': 'https://www.fdic.gov/news/press-releases/rss.xml',
                        'source_name_override': 'Federal Deposit Insurance Corporation'
                    },
                    # OCC Acting Comptroller Statements
                    {
                        'name': 'OCC News Releases',
                        'url': 'https://www.occ.treas.gov/news-issuances/news-releases/rss.xml',
                        'source_name_override': 'Office of the Comptroller of the Currency'
                    },
                    # CFPB Director (Rohit Chopra) - Speeches/Testimony
                    {
                        'name': 'CFPB Director Speeches',
                        'url': 'https://www.consumerfinance.gov/about-us/newsroom/speeches.rss',
                        'source_name_override': 'CFPB Director'
                    },
                    # Federal Reserve Governor (Michelle Bowman) - Speeches
                    {
                        'name': 'Federal Reserve Governor Speeches',
                        'url': 'https://www.federalreserve.gov/feeds/press_speech.xml',
                        'source_name_override': 'Federal Reserve Governor'
                    }
                ],
                'timeout': 30,
                'rate_limit_delay': 1.0
            }
            self._public_statement_connector = PublicStatementConnector(public_statement_config)
        else:
            self._public_statement_connector = None

    def get_source_metadata(self, source_name: str):
        return self._catalog.get(source_name)

    def get_cfpb_connector(self):
        """
        Get the CFPB connector instance for Tier 1 migration.
        
        Returns:
            CFPBConnector instance if available, None otherwise
        """
        return self._cfpb_connector

    def get_legiscan_connector(self):
        """
        Get the LegiScan connector instance for Tier 1 migration.
        
        Returns:
            LegiScanConnector instance if available, None otherwise
        """
        return self._legiscan_connector

    def get_research_connector(self):
        """
        Get the Research connector instance for Phase 4 implementation.
        
        Returns:
            ResearchConnector instance if available, None otherwise
        """
        return self._research_connector

    def get_policymaker_connector(self):
        """
        Get the Policymaker connector instance for Phase 5 implementation.
        
        Returns:
            PolicymakerConnector instance if available, None otherwise
        """
        return self._policymaker_connector

    def get_news_connector(self):
        """
        Get the News connector instance for Phase 6 implementation.
        
        Returns:
            NewsConnector instance if available, None otherwise
        """
        return self._news_connector

    def get_public_statement_connector(self):
        """
        Get the Public Statement connector instance for Phase 7 implementation.
        
        Returns:
            PublicStatementConnector instance if available, None otherwise
        """
        return self._public_statement_connector

    def update_source_health(self, source_name: str, success: bool, error: str = None):
        if source_name in self._catalog:
            # For senate_banking_committee, treat 503 as temporary unavailability
            source_config = self._catalog[source_name]
            if source_name == "senate_banking_committee" and error and "503" in str(error):
                # Log as temporary issue but don't mark as failed
                source_config["last_error"] = "Source temporarily unavailable (503)"
                # Don't update last_success to avoid marking as failed
            else:
                self._catalog[source_name]["last_success"] = datetime.datetime.now().isoformat() if success else self._catalog[source_name]["last_success"]
                self._catalog[source_name]["last_error"] = error

    def list_enabled_sources(self) -> list:
        return [name for name, meta in self._catalog.items() if meta["enabled"]]

    def get_enabled_sources_by_type(self, source_type: str) -> list:
        return [name for name, meta in self._catalog.items() if meta["enabled"] and meta["source_type"] == source_type]

    def get_fallback_data(self, source_name: str):
        """Get fallback data for a source when it's unavailable"""
        source_config = self._catalog.get(source_name, {})
        if source_config.get("fallback_enabled") and "fallback_data" in source_config:
            return source_config["fallback_data"]
        return []