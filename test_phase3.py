import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.insert(0, '.')

from infrastructure.config import load_config
from agents.orchestrator import PolicyOrchestratorAgent

class TestPhase3OrchestratorDelegation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.config = load_config()
        self.config.swarm_mode = "production"
        self.orchestrator = PolicyOrchestratorAgent()
        self.orchestrator.config = self.config

    def test_production_mode_delegates_to_legislative_monitor(self):
        """Test that in production mode, the orchestrator delegates to LegislativeMonitorAgent."""
        # Create a legislative task
        task_id = 'test-leg-task-1'
        task = {
            'id': task_id,
            'type': 'legislative_monitoring',
            'description': 'Test legislative monitoring',
            'jurisdiction': 'US Federal',
            'product': 'Buy Now, Pay Later',
            'priority': 'high',
            'assigned_agent_type': 'legislative_monitor',
            'dependencies': [],
            'estimated_duration': 300,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'status': 'in_progress',  # Start with in_progress to trigger monitoring logic
            'started_at': datetime.now(timezone.utc).isoformat()
        }
        self.orchestrator.active_tasks[task_id] = task

        # Mock the LegislativeMonitorAgent.execute_task to return a success result
        with patch('agents.legislative_monitor.LegislativeMonitorAgent.execute_task') as mock_execute:
            mock_execute.return_value = {
                'status': 'success',
                'message': 'Legislative monitoring completed successfully',
                'legislative_items_found': 5,
                'relevant_items': 3,
                'analyzed_items': [],
                'summary': 'Found 5 legislative items, 3 relevant'
            }

            # Call _monitor_progress - this should delegate to the agent
            result = self.orchestrator._monitor_progress({})

            # Verify the mock was called (delegation happened)
            mock_execute.assert_called_once()

            # Verify the call was made with the expected payload
            call_args = mock_execute.call_args[0][0]
            self.assertEqual(call_args['type'], 'legislative_monitoring')
            self.assertEqual(call_args['jurisdiction'], 'US Federal')
            self.assertEqual(call_args['product'], 'Buy Now, Pay Later')
            self.assertEqual(call_args['lookback_hours'], 24)

            # Verify the task was marked as completed based on worker result
            self.assertEqual(len(self.orchestrator.active_tasks), 0)
            self.assertEqual(len(self.orchestrator.completed_tasks), 1)
            self.assertEqual(len(self.orchestrator.failed_tasks), 0)

            completed_task = self.orchestrator.completed_tasks[0]
            self.assertEqual(completed_task['id'], task_id)
            self.assertEqual(completed_task['status'], 'completed')
            self.assertEqual(completed_task['result']['status'], 'success')

    def test_production_mode_handles_agent_failure(self):
        """Test that orchestrator marks task as failed when worker agent fails."""
        # Create a legislative task
        task_id = 'test-leg-task-2'
        task = {
            'id': task_id,
            'type': 'legislative_monitoring',
            'description': 'Test legislative monitoring',
            'jurisdiction': 'US Federal',
            'product': 'Buy Now, Pay Later',
            'priority': 'high',
            'assigned_agent_type': 'legislative_monitor',
            'dependencies': [],
            'estimated_duration': 300,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'status': 'in_progress',
            'started_at': datetime.now(timezone.utc).isoformat()
        }
        self.orchestrator.active_tasks[task_id] = task

        # Mock the LegislativeMonitorAgent.execute_task to return an error
        with patch('agents.legislative_monitor.LegislativeMonitorAgent.execute_task') as mock_execute:
            mock_execute.return_value = {
                'status': 'error',
                'message': 'API rate limit exceeded',
                'legislative_items_found': 0
            }

            # Call _monitor_progress
            result = self.orchestrator._monitor_progress({})

            # Verify the task was moved to failed
            self.assertEqual(len(self.orchestrator.active_tasks), 0)
            self.assertEqual(len(self.orchestrator.completed_tasks), 0)
            self.assertEqual(len(self.orchestrator.failed_tasks), 1)

            failed_task = self.orchestrator.failed_tasks[0]
            self.assertEqual(failed_task['id'], task_id)
            self.assertEqual(failed_task['status'], 'failed')
            self.assertEqual(failed_task['failure_reason'], 'API rate limit exceeded')

    def test_production_mode_handles_agent_exception(self):
        """Test that orchestrator marks task as failed when worker agent raises exception."""
        # Create a legislative task
        task_id = 'test-leg-task-3'
        task = {
            'id': task_id,
            'type': 'legislative_monitoring',
            'description': 'Test legislative monitoring',
            'jurisdiction': 'US Federal',
            'product': 'Buy Now, Pay Later',
            'priority': 'high',
            'assigned_agent_type': 'legislative_monitor',
            'dependencies': [],
            'estimated_duration': 300,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'status': 'in_progress',
            'started_at': datetime.now(timezone.utc).isoformat()
        }
        self.orchestrator.active_tasks[task_id] = task

        # Mock the LegislativeMonitorAgent.execute_task to raise an exception
        with patch('agents.legislative_monitor.LegislativeMonitorAgent.execute_task') as mock_execute:
            mock_execute.side_effect = Exception("Network timeout")

            # Call _monitor_progress
            result = self.orchestrator._monitor_progress({})

            # Verify the task was moved to failed
            self.assertEqual(len(self.orchestrator.active_tasks), 0)
            self.assertEqual(len(self.orchestrator.completed_tasks), 0)
            self.assertEqual(len(self.orchestrator.failed_tasks), 1)

            failed_task = self.orchestrator.failed_tasks[0]
            self.assertEqual(failed_task['id'], task_id)
            self.assertEqual(failed_task['status'], 'failed')
            self.assertEqual(failed_task['failure_reason'], 'Network timeout')

    def test_development_mode_still_uses_simulation(self):
        """Test that development/mock mode still uses simulation (not delegation)."""
        # Set to development mode
        self.config.swarm_mode = "development"
        self.orchestrator.config = self.config

        # Create a legislative task
        task_id = 'test-leg-task-4'
        task = {
            'id': task_id,
            'type': 'legislative_monitoring',
            'description': 'Test legislative monitoring',
            'jurisdiction': 'US Federal',
            'product': 'Buy Now, Pay Later',
            'priority': 'high',
            'assigned_agent_type': 'legislative_monitor',
            'dependencies': [],
            'estimated_duration': 300,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'status': 'in_progress',
            'started_at': datetime.now(timezone.utc).isoformat()
        }
        self.orchestrator.active_tasks[task_id] = task

        # Mock random.random to return a value that triggers completion
        with patch('agents.orchestrator.random') as mock_random:
            mock_random.random.return_value = 0.9  # > 0.8, should trigger completion

            # Call _monitor_progress
            result = self.orchestrator._monitor_progress({})

            # Verify the task was moved to completed via simulation
            self.assertEqual(len(self.orchestrator.active_tasks), 0)
            self.assertEqual(len(self.orchestrator.completed_tasks), 1)
            self.assertEqual(len(self.orchestrator.failed_tasks), 0)

            completed_task = self.orchestrator.completed_tasks[0]
            self.assertEqual(completed_task['id'], task_id)
            self.assertEqual(completed_task['status'], 'completed')

    def test_no_random_in_production_path(self):
        """Test that random.random is NOT used in the production path."""
        # Create a legislative task
        task_id = 'test-leg-task-5'
        task = {
            'id': task_id,
            'type': 'legislative_monitoring',
            'description': 'Test legislative monitoring',
            'jurisdiction': 'US Federal',
            'product': 'Buy Now, Pay Later',
            'priority': 'high',
            'assigned_agent_type': 'legislative_monitor',
            'dependencies': [],
            'estimated_duration': 300,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'status': 'in_progress',
            'started_at': datetime.now(timezone.utc).isoformat()
        }
        self.orchestrator.active_tasks[task_id] = task

        # Mock random.random to ensure it's NOT called in production mode
        with patch('agents.orchestrator.random') as mock_random:
            # Mock the LegislativeMonitorAgent.execute_task
            with patch('agents.legislative_monitor.LegislativeMonitorAgent.execute_task') as mock_execute:
                mock_execute.return_value = {
                    'status': 'success',
                    'message': 'Success'
                }

                # Call _monitor_progress
                result = self.orchestrator._monitor_progress({})

                # Verify random.random was NOT called
                mock_random.random.assert_not_called()

                # Verify the agent WAS called
                mock_execute.assert_called_once()

if __name__ == '__main__':
    unittest.main()
