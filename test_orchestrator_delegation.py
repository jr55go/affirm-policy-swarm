import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.insert(0, '.')

from infrastructure.config import load_config
from agents.orchestrator import PolicyOrchestratorAgent

class TestOrchestratorDelegation(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.config.swarm_mode = "production"
        self.orchestrator = PolicyOrchestratorAgent()
        self.orchestrator.config = self.config

    def test_legislative_task_delegation_success(self):
        # Create a legislative task
        task_id = 'test-task-1'
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

        # Mock the LegislativeMonitorAgent.execute_task to return success
        with patch('agents.legislative_monitor.LegislativeMonitorAgent.execute_task') as mock_execute:
            mock_execute.return_value = {
                'status': 'success',
                'message': 'Task completed successfully',
                'data': {}
            }

            # Call _monitor_progress
            result = self.orchestrator._monitor_progress({})

            # Check that the task was moved to completed
            self.assertEqual(len(self.orchestrator.active_tasks), 0)
            self.assertEqual(len(self.orchestrator.completed_tasks), 1)
            self.assertEqual(len(self.orchestrator.failed_tasks), 0)

            completed_task = self.orchestrator.completed_tasks[0]
            self.assertEqual(completed_task['id'], task_id)
            self.assertEqual(completed_task['status'], 'completed')
            self.assertIn('result', completed_task)
            self.assertEqual(completed_task['result']['status'], 'success')

            # Check that the mock was called with the expected payload
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args[0][0]
            self.assertEqual(call_args['type'], 'legislative_monitoring')
            self.assertEqual(call_args['jurisdiction'], 'US Federal')
            self.assertEqual(call_args['product'], 'Buy Now, Pay Later')

    def test_legislative_task_delegation_failure(self):
        # Create a legislative task
        task_id = 'test-task-2'
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

        # Mock the LegislativeMonitorAgent.execute_task to return failure
        with patch('agents.legislative_monitor.LegislativeMonitorAgent.execute_task') as mock_execute:
            mock_execute.return_value = {
                'status': 'error',
                'message': 'Agent failed',
                'data': {}
            }

            # Call _monitor_progress
            result = self.orchestrator._monitor_progress({})

            # Check that the task was moved to failed
            self.assertEqual(len(self.orchestrator.active_tasks), 0)
            self.assertEqual(len(self.orchestrator.completed_tasks), 0)
            self.assertEqual(len(self.orchestrator.failed_tasks), 1)

            failed_task = self.orchestrator.failed_tasks[0]
            self.assertEqual(failed_task['id'], task_id)
            self.assertEqual(failed_task['status'], 'failed')
            self.assertEqual(failed_task['failure_reason'], 'Agent failed')

    def test_legislative_task_delegation_exception(self):
        # Create a legislative task
        task_id = 'test-task-3'
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
            mock_execute.side_effect = Exception("Something went wrong")

            # Call _monitor_progress
            result = self.orchestrator._monitor_progress({})

            # Check that the task was moved to failed
            self.assertEqual(len(self.orchestrator.active_tasks), 0)
            self.assertEqual(len(self.orchestrator.completed_tasks), 0)
            self.assertEqual(len(self.orchestrator.failed_tasks), 1)

            failed_task = self.orchestrator.failed_tasks[0]
            self.assertEqual(failed_task['id'], task_id)
            self.assertEqual(failed_task['status'], 'failed')
            self.assertEqual(failed_task['failure_reason'], 'Something went wrong')

if __name__ == '__main__':
    unittest.main()
