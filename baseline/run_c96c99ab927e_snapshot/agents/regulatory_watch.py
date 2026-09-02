"""
Regulatory Watch Agent for the Affirm Policy Swarm.
Responsible for monitoring agency rulemaking, guidance, enforcement actions.
"""

import time
import uuid
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from load_swarm_jobs import load_swarm_jobs

from .base_agent import BaseAgent
from infrastructure.config import load_config
from infrastructure.database import neo4j_session

# Import sentiment analysis tool
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from sentiment_tool import analyze_sentiment


class RegulatoryWatchAgent(BaseAgent):
    SWARM_ID = "affirm_policy_swarm"
    PROJECT_SCOPE = "affirm_bnpl_policy"
    """Regulatory Watch Agent for monitoring regulatory activity."""
    
    def __init__(self, agent_id: str = None):
        super().__init__(agent_id or f"reg-watch-{str(uuid.uuid4())[:8]}", "Regulatory Watch Agent")
        self.config = load_config()
        
    def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute regulatory monitoring tasks."""
        task_type = task_data.get("type", "unknown")
        
        self.log_thought(f"Regulatory Watch agent received task: {task_type}")
        
        if task_type == "monitor_regulations":
            return self._monitor_regulations(task_data)
        elif task_type == "track_rulemaking":
            return self._track_rulemaking(task_data)
        elif task_type == "analyze_guidance":
            return self._analyze_guidance(task_data)
        elif task_type == "check_enforcement":
            return self._check_enforcement(task_data)
        else:
            return {
                "status": "error",
                "message": f"Unknown task type: {task_type}",
                "agent_id": self.agent_id
            }
            
    def _monitor_regulations(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor regulatory activity for assigned jurisdictions and products."""
        jurisdiction = task_data.get("jurisdiction", "US Federal")
        product = task_data.get("product", "Buy Now, Pay Later")
        lookback_hours = task_data.get("lookback_hours", 24)
        agencies = task_data.get("agencies", self._get_default_agencies(jurisdiction))
        
        self.log_thought(f"Monitoring regulations for {product} in {jurisdiction} (last {lookback_hours}h)")
        self.log_thought(f"Watching agencies: {', '.join(agencies)}")
        
        # CRITICAL INSTRUCTION - DEDUPLICATION: Check if we've recently monitored this jurisdiction/product
        lookup_key = f"reg_watch:{jurisdiction}:{product}:{lookback_hours}"
        recent_monitoring = self.check_redis_deduplication(lookup_key)
        if recent_monitoring:
            self.log_thought(f"Recent regulatory monitoring found for {lookup_key}, checking for updates")
            # Check if there's been significant change since last monitoring
            last_run = recent_monitoring.get("completed_at")
            if last_run:
                try:
                    last_run_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                    hours_since = (datetime.now(timezone.utc) - last_run_dt).total_seconds() / 3600
                    
                    if hours_since < 2:  # Less than 2 hours since last check (regulatory changes slower)
                        self.log_thought(f"Recent check was {hours_since:.1f}h ago, returning cached result")
                        return {
                            "status": "cached",
                            "agent_id": self.agent_id,
                            "jurisdiction": jurisdiction,
                            "product": product,
                            "data_source": "cache",
                            "cached_result": recent_monitoring,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                except Exception as e:
                    self.log_thought(f"Error parsing timestamp: {e}")
        
        # In a real implementation, this would call regulatory APIs (Federal Register, eCFR, agency websites)
        # For now, we'll simulate the monitoring process
        
        # Simulate fetching regulatory data
        regulatory_items = self._fetch_regulatory_data(jurisdiction, product, lookback_hours, agencies)
        
        # Process and analyze the regulatory items
        analyzed_items = self._analyze_regulatory_items(regulatory_items, product)
        
        # Store results in graph database for future reference
        self._store_regulatory_results(jurisdiction, product, analyzed_items)
        
        # Store monitoring result in Redis for deduplication
        monitoring_result = {
            "jurisdiction": jurisdiction,
            "product": product,
            "lookback_hours": lookback_hours,
            "agencies_watched": agencies,
            "items_found": len(regulatory_items),
            "relevant_items": len(analyzed_items),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "summary": self._generate_regulatory_summary(analyzed_items)
        }
        
        self.store_redis_deduplication(lookup_key, monitoring_result, expire_seconds=7200)  # 2 hours
        
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "jurisdiction": jurisdiction,
            "product": product,
            "lookback_hours": lookback_hours,
            "agencies_watched": agencies,
            "regulatory_items_found": len(regulatory_items),
            "relevant_items": len(analyzed_items),
            "analyzed_items": analyzed_items[:5],  # Return first 5 for brevity
            "summary": monitoring_result["summary"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    def _get_default_agencies(self, jurisdiction: str) -> List[str]:
        """Get default regulatory agencies for jurisdiction."""
        if jurisdiction == "US Federal":
            return ["CFPB", "Federal Reserve", "OCC", "FDIC", "NCUA", "FTC"]
        elif jurisdiction == "California":
            return ["DFPI", "CA Attorney General", "CA Department of Financial Protection and Innovation"]
        elif jurisdiction == "New York":
            return ["NYDFS", "NY Attorney General"]
        elif jurisdiction == "Texas":
            return ["OCCC", "TX Attorney General"]
        else:
            return ["Financial Regulator"]  # Generic
            
    def _fetch_regulatory_data(self, jurisdiction: str, product: str, lookback_hours: int, 
                           agencies: List[str]) -> List[Dict[str, Any]]:
        """Fetch regulatory data from sources (simulated)."""
        self.log_thought(f"Fetching regulatory data for {jurisdiction} - {product}")
        
        # In reality, this would:
        # 1. Call Federal Register API for US federal regulations
        # 2. Access eCFR for current regulations
        # 3. Monitor agency websites for guidance and bulletins
        # 4. Check enforcement action databases
        # 5. Filter by date range and product relevance
        
        # For simulation, return mock data based on jurisdiction and agencies
        mock_items = []
        
        if jurisdiction == "US Federal":
            mock_items = [
                {
                    "agency": "CFPB",
                    "type": "guidance",
                    "title": "CFPB Issues Guidance on Buy Now, Pay Later Products",
                    "reference": "CFPB Circular 2026-03",
                    "issued_date": "2026-06-05",
                    "effective_date": "2026-07-05",
                    "url": "https://www.consumerfinance.gov/compliance/circulars/circular-2026-03/",
                    "keywords": ["BNPL", "point of sale lending", "installment loans", "disclosures"],
                    "relevance_score": 0.95
                },
                {
                    "agency": "Federal Reserve",
                    "type": "rulemaking",
                    "title": "Proposed Rule: Interest Rate Disclosures for Alternative Payment Products",
                    "reference": "Docket No. R-1687",
                    "issued_date": "2026-06-01",
                    "comment_deadline": "2026-07-15",
                    "url": "https://www.federalreserve.gov/bankinforeg/proposedrules.htm",
                    "keywords": ["APR", "disclosure", "alternative payment"],
                    "relevance_score": 0.8
                },
                {
                    "agency": "FTC",
                    "type": "enforcement",
                    "title": "FTC Settles Case Regarding Deceptive BNPL Marketing Practices",
                    "reference": "FTC Docket 9377",
                    "issued_date": "2026-05-28",
                    "settlement_amount": "$2.5M",
                    "url": "https://www.ftc.gov/news-events/news/press-releases/2026/05/ftc-settles-case",
                    "keywords": ["marketing", "deceptive practices", "BNPL"],
                    "relevance_score": 0.75
                }
            ]
        elif jurisdiction == "California":
            mock_items = [
                {
                    "agency": "DFPI",
                    "type": "guidance",
                    "title": "DFPI Issues Guidance on California Financing Law Disclosures",
                    "reference": "DFPI Guidance 2026-02",
                    "issued_date": "2026-06-03",
                    "effective_date": "2026-06-15",
                    "url": "https://dfpi.ca.gov/guidance/2026-02/",
                    "keywords": ["CFL", "disclosure", "consumer loans"],
                    "relevance_score": 0.85
                }
            ]
        
        # Filter by relevance score and agency match
        relevant_items = [
            item for item in mock_items 
            if item.get("relevance_score", 0) >= 0.6 
            and item.get("agency") in agencies
        ]
        
        self.log_thought(f"Found {len(mock_items)} regulatory items, {len(relevant_items)} relevant for {product}")
        return relevant_items
        
    def _analyze_regulatory_items(self, items: List[Dict[str, Any]], product: str) -> List[Dict[str, Any]]:
        """Analyze regulatory items for potential impact on Affirm products."""
        self.log_thought(f"Analyzing {len(items)} regulatory items for {product} impact")
        
        analyzed = []
        for item in items:
            # In a real implementation, this would use LLM to analyze the regulation/guidance text
            # For now, we'll do rule-based analysis
            
            # Perform sentiment analysis on the title and reference text
            text_for_sentiment = f"{item.get('title', '')} {item.get('reference', '')}"
            sentiment_score = analyze_sentiment(text_for_sentiment)
            
            analysis = {
                "item_id": f"{item.get('agency')}-{item.get('type')}-{hashlib.md5(item.get('title', '').encode()).hexdigest()[:8]}",
                "agency": item.get("agency"),
                "type": item.get("type"),  # guidance, rulemaking, enforcement, notice
                "title": item.get("title"),
                "reference": item.get("reference"),
                "jurisdiction": item.get("jurisdiction", "US Federal"),  # Would be set from context
                "product": product,
                "relevance_score": item.get("relevance_score", 0.5),
                "sentiment_score": sentiment_score,  # Add sentiment analysis score
                "potential_impact": self._assess_potential_impact(item, product),
                "key_concerns": self._identify_key_concerns(item, product),
                "required_action": self._determine_required_action(item, product),
                "compliance_deadline": item.get("effective_date") or item.get("comment_deadline"),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "analyst_agent": self.agent_id
            }
            
            analyzed.append(analysis)
            
        # Sort by relevance score and potential impact
        analyzed.sort(key=lambda x: (x["relevance_score"], x["potential_impact"]), reverse=True)
        return analyzed
        
    def _assess_potential_impact(self, item: Dict[str, Any], product: str) -> str:
        """Assess potential impact of regulation on product."""
        title = item.get("title", "").lower()
        reference = item.get("reference", "").lower()
        keywords = [k.lower() for k in item.get("keywords", [])]
        item_type = item.get("type", "").lower()
        
        text_to_check = f"{title} {reference} {' '.join(keywords)} {item_type}"
        
        # High impact indicators
        high_impact_terms = [
            "ban", "prohibit", "strict limitation", "interest rate cap", 
            "fee restriction", "mandatory disclosure", "required licensing",
            "enforcement action", "settlement", "fine", "penalty"
        ]
        medium_impact_terms = [
            "guidance", "clarification", "interpretation", "best practice",
            "reporting requirement", "record keeping", "audit"
        ]
        low_impact_terms = [
            "notice", "information", "outreach", "educational", "workshop"
        ]
        
        if any(term in text_to_check for term in high_impact_terms):
            return "high"
        elif any(term in text_to_check for term in medium_impact_terms):
            return "medium"
        elif any(term in text_to_check for term in low_impact_terms):
            return "low"
        else:
            return "minimal"
            
    def _identify_key_concerns(self, item: Dict[str, Any], product: str) -> List[str]:
        """Identify key concerns from regulation for Affirm."""
        concerns = []
        title = item.get("title", "").lower()
        reference = item.get("reference", "").lower()
        keywords = [k.lower() for k in item.get("keywords", [])]
        item_type = item.get("type", "").lower()
        
        text_to_check = f"{title} {reference} {' '.join(keywords)} {item_type}"
        
        # Product-specific concerns
        if "bnpl" in text_to_check or "point of sale" in text_to_check or "installment loan" in text_to_check:
            if "apr" in text_to_check or "interest" in text_to_check:
                concerns.append("Potential APR/interest rate restrictions or disclosure requirements")
            if "fee" in text_to_check:
                concerns.append("Potential fee limitations, bans, or new disclosure requirements")
            if "disclosure" in text_to_check:
                concerns += [
                    "Enhanced disclosure requirements", 
                    "Potential changes to T&C presentation",
                    "New timing or format requirements for disclosures"
                ]
            if "licens" in text_to_check or "register" in text_to_check:
                concerns.append("Potential new licensing or registration requirements")
            if "audit" in text_to_check or "examination" in text_to_check:
                concerns.append("Increased regulatory examination or audit scope")
                
        # Agency-specific concerns
        agency = item.get("agency", "")
        if agency == "CFPB":
            if "UDAAP" in text_to_check or "unfair" in text_to_check:
                concerns.append("Potential UDAAP (Unfair, Deceptive, Abusive Acts or Practices) concerns")
            if "marketing" in text_to_check or "advertising" in text_to_check:
                concerns.append("Marketing and advertising practice scrutiny")
        elif agency == "Federal Reserve":
            if "truth in lending" in text_to_check or "tila" in text_to_check:
                concerns.append("Truth in Lending Act (TILA) compliance implications")
            if "equal credit opportunity" in text_to_check or "ecoa" in text_to_check:
                concerns.append("Equal Credit Opportunity Act (ECOA) implications")
        elif agency == "FTC":
            if "deceptive" in text_to_check:
                concerns.append("Deceptive marketing or advertising practices")
            if "privacy" in text_to_check:
                concerns.append("Consumer privacy and data protection concerns")
                
        # Type-specific concerns
        if item_type == "enforcement":
            concerns.append("Active enforcement action indicates regulatory priority")
        elif item_type == "rulemaking":
            concerns.append("Upcoming rule changes may require operational adjustments")
        elif item_type == "guidance":
            concerns.append("Guidance reflects current regulatory thinking and priorities")
            
        return list(set(concerns))  # Remove duplicates
        
    def _determine_required_action(self, item: Dict[str, Any], product: str) -> str:
        """Determine required action based on regulatory analysis."""
        impact = self._assess_potential_impact(item, product)
        concerns = self._identify_key_concerns(item, product)
        item_type = item.get("type", "").lower()
        
        # Immediate actions for enforcement and high-impact rules
        if item_type == "enforcement" or impact == "high":
            if "settlement" in item or "fine" in item:
                return f"Immediate legal review; assess similar practice exposure"
            return "Immediate review by legal, compliance, and product teams"
            
        # Actions for rulemaking and guidance
        elif item_type in ["rulemaking", "guidance"]:
            if impact == "high" or len(concerns) > 2:
                return "Review draft/comment period; prepare formal comment if needed"
            elif impact == "medium":
                return "Monitor for finalization; assess operational impact"
            else:
                return "Continue monitoring; low immediate concern"
                
        # Actions for notices
        elif item_type == "notice":
            return "Informational only; file for reference"
            
        # Default
        else:
            return "Continue routine monitoring"
            
    def _store_regulatory_results(self, jurisdiction: str, product: str, 
                                analyzed_items: List[Dict[str, Any]]) -> bool:
        """Store regulatory monitoring results in Neo4j graph."""
        if not self.neo4j_driver:
            self.logger.warning("Neo4j driver not available for storing results")
            return False
            
        try:
            with neo4j_session() as session:
                # Create or update regulatory monitoring record
                query = """
                MERGE (r:RegulatoryMonitoring {
                    jurisdiction: $jurisdiction,
                    product: $product,
                    monitoring_period: $period
                    swarm_id: $swarm_id,
                    project_scope: $project_scope
                })
                SET r.items_analyzed = $items_count,
                    r.relevant_items = $relevant_count,
                    r.last_updated = $timestamp,
                    r.analysis_data = $analysis_data
                RETURN r.id as record_id
                """
                result = session.run(query, 
                                   jurisdiction=jurisdiction,
                                   product=product,
                                   monitoring_period=f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')} (24h)",
                                   items_count=len(self._fetch_regulatory_data(jurisdiction, product, 24, self._get_default_agencies(jurisdiction))),  # This would be cached in reality
                                   relevant_count=len(analyzed_items),
                                   timestamp=datetime.now(timezone.utc).isoformat(),
                                   swarm_id=self.SWARM_ID,
                                   project_scope=self.PROJECT_SCOPE,
                                   analysis_data=json.dumps(analyzed_items))
                record = result.single()
                
                if record:
                    self.logger.debug(f"Stored regulatory monitoring results for {jurisdiction}:{product}")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Error storing regulatory results: {e}")
            return False
            
    def _generate_regulatory_summary(self, analyzed_items: List[Dict[str, Any]]) -> str:
        """Generate a human-readable summary of regulatory monitoring results."""
        if not analyzed_items:
            return "No relevant regulatory activity detected"
            
        high_count = sum(1 for item in analyzed_items if item.get("potential_impact") == "high")
        medium_count = sum(1 for item in analyzed_items if item.get("potential_impact") == "medium")
        low_count = sum(1 for item in analyzed_items if item.get("potential_impact") == "low")
        
        # Count by type
        guidance_count = sum(1 for item in analyzed_items if item.get("type") == "guidance")
        rulemaking_count = sum(1 for item in analyzed_items if item.get("type") == "rulemaking")
        enforcement_count = sum(1 for item in analyzed_items if item.get("type") == "enforcement")
        
        summary_parts = []
        if high_count > 0:
            summary_parts.append(f"{high_count} high-impact items")
        if medium_count > 0:
            summary_parts.append(f"{medium_count} medium-impact items")
        if low_count > 0:
            summary_parts.append(f"{low_count} low-impact items")
            
        type_parts = []
        if guidance_count > 0:
            type_parts.append(f"{guidance_count} guidance")
        if rulemaking_count > 0:
            type_parts.append(f"{rulemaking_count} rulemaking")
        if enforcement_count > 0:
            type_parts.append(f"{enforcement_count} enforcement actions")
            
        summary = f"Regulatory monitoring found: {', '.join(summary_parts)}"
        if type_parts:
            summary += f" ({', '.join(type_parts)})"
            
        return summary
        
    def _track_rulemaking(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track a specific rulemaking proceeding."""
        agency = task_data.get("agency", "")
        rule_id = task_data.get("rule_id", "")
        docket_number = task_data.get("docket_number", "")
        
        self.log_thought(f"Tracking rulemaking {rule_id} from {agency} (docket: {docket_number})")
        
        # In reality, this would set up continuous tracking of a specific rulemaking
        # For simulation, return tracking setup confirmation
        
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "agency": agency,
            "rule_id": rule_id,
            "docket_number": docket_number,
            "tracking_established": True,
            "tracking_frequency": "daily",
            "comment_deadline_monitoring": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    def _analyze_guidance(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze regulatory guidance or interpretive documents."""
        agency = task_data.get("agency", "")
        guidance_id = task_data.get("guidance_id", "")
        title = task_data.get("title", "")
        
        self.log_thought(f"Analyzing guidance {guidance_id} from {agency}: {title}")
        
        # In reality, this would analyze guidance text for impact
        # For simulation, return basic analysis
        
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "agency": agency,
            "guidance_id": guidance_id,
            "title": title,
            "guidance_analyzed": True,
            "impact_assessment": "Analysis would be performed in production",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    def _check_enforcement(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for recent enforcement actions."""
        agency = task_data.get("agency", "")
        lookback_days = task_data.get("lookback_days", 30)
        
        self.log_thought(f"Checking {agency} enforcement actions (last {lookback_days} days)")
        
        # In reality, this would query enforcement databases
        # For simulation, return basic check
        
        return {
            "status": "success",
            "agent_id": self.agent_id,
            "agency": agency,
            "lookback_days": lookback_days,
            "enforcement_checked": True,
            "actions_found": 0,  # Would be actual count in production
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this agent provides."""
        return [
            "regulatory_monitoring",
            "rulemaking_tracking",
            "guidance_analysis",
            "enforcement_action_checking",
            "agency_specific_monitoring",
            "impact_assessment",
            "deduplication_enforcement",
            "graph_database_storage",
            "compliance_deadline_tracking"
        ]


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    agent = RegulatoryWatchAgent()
    
    # Test regulatory monitoring
    result = agent.execute_task({
        "type": "monitor_regulations",
        "jurisdiction": "US Federal",
        "product": "Buy Now, Pay Later",
        "lookback_hours": 24
    })
    
    print("Regulatory monitoring result:")
    print(f"Status: {result['status']}")
    print(f"Jurisdiction: {result.get('jurisdiction')}")
    print(f"Product: {result.get('product')}")
    print(f"Items found: {result.get('regulatory_items_found')}")
    print(f"Relevant items: {result.get('relevant_items')}")
    print(f"Summary: {result.get('summary')}")