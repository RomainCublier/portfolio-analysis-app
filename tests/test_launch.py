import unittest
from scripts.start_app import launch_args


class LaunchTests(unittest.TestCase):
    def test_host_port_is_used_without_shell_interpolation(self):
        args = launch_args('8080')
        self.assertIn('--server.port=8080', args)
        self.assertIn('--server.address=0.0.0.0', args)
        self.assertIn('--browser.gatherUsageStats=false', args)

    def test_invalid_ports_are_rejected(self):
        for value in ['0', '65536', '-1', 'abc', '8501; echo test']:
            with self.assertRaises(ValueError):
                launch_args(value)
