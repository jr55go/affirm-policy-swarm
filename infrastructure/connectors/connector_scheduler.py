import heapq
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import IntEnum


class Tier(IntEnum):
    """Priority tiers for connector scheduling."""
    TIER_1 = 1  # Highest priority - most frequent
    TIER_2 = 2
    TIER_3 = 3
    TIER_4 = 4
    TIER_5 = 5
    TIER_6 = 6  # Lowest priority - least frequent


@dataclass
class ScheduledTask:
    """Represents a scheduled connector run."""
    source_name: str
    tier: Tier
    interval_seconds: int
    next_run: float = field(default_factory=time.time)
    last_run: Optional[float] = None
    run_count: int = 0
    
    def __lt__(self, other):
        """For priority queue ordering - lower next_run time has higher priority."""
        return self.next_run < other.next_run


class Scheduler:
    """Manages scheduling of connector runs based on tier priorities."""
    
    # Base intervals in seconds for each tier (can be overridden in config)
    BASE_INTERVALS = {
        Tier.TIER_1: 3600,      # 1 hour
        Tier.TIER_2: 7200,      # 2 hours
        Tier.TIER_3: 21600,     # 6 hours
        Tier.TIER_4: 43200,     # 12 hours
        Tier.TIER_5: 86400,     # 1 day
        Tier.TIER_6: 604800,    # 1 week
    }
    
    def __init__(self):
        self._scheduled_tasks: Dict[str, ScheduledTask] = {}
        self._priority_queue: List[ScheduledTask] = []
    
    def register_source(self, source_name: str, tier: Tier, custom_interval: Optional[int] = None) -> None:
        """Register a source for scheduling.
        
        Args:
            source_name: Name of the data source
            tier: Priority tier (1-6)
            custom_interval: Optional custom interval in seconds (overrides tier default)
        """
        interval = custom_interval if custom_interval is not None else self.BASE_INTERVALS[tier]
        now = time.time()
        
        task = ScheduledTask(
            source_name=source_name,
            tier=tier,
            interval_seconds=interval,
            next_run=now,
            last_run=None,
            run_count=0
        )
        
        self._scheduled_tasks[source_name] = task
        heapq.heappush(self._priority_queue, task)
    
    def get_next_due(self) -> Optional[Tuple[str, float]]:
        """Get the next source that is due to run.
        
        Returns:
            Tuple of (source_name, seconds_until_due) or None if no tasks
        """
        if not self._priority_queue:
            return None
            
        # Peek at the next task without popping
        now = time.time()
        next_task = self._priority_queue[0]
        
        if next_task.next_run <= now:
            return (next_task.source_name, 0.0)
        else:
            return (next_task.source_name, next_task.next_run - now)
    
    def mark_run(self, source_name: str) -> None:
        """Mark a source as having just run, rescheduling it.
        
        Args:
            source_name: Name of the source that just ran
        """
        if source_name not in self._scheduled_tasks:
            return
            
        task = self._scheduled_tasks[source_name]
        now = time.time()
        
        # Update the task
        task.last_run = now
        task.run_count += 1
        task.next_run = now + task.interval_seconds
        
        # Re-heapify the priority queue since the priority changed
        heapq.heapify(self._priority_queue)
    
    def get_status(self) -> Dict[str, dict]:
        """Get the current status of all scheduled sources.
        
        Returns:
            Dictionary mapping source names to their status information
        """
        now = time.time()
        status = {}
        
        for source_name, task in self._scheduled_tasks.items():
            status[source_name] = {
                "tier": task.tier.name,
                "interval_seconds": task.interval_seconds,
                "last_run": task.last_run,
                "next_run": task.next_run,
                "seconds_until_next": max(0, task.next_run - now),
                "run_count": task.run_count
            }
            
        return status