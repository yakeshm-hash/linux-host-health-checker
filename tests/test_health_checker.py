import unittest

from health_checker import (
    parse_cpu_line,
    parse_meminfo,
    check_thresholds
)


class TestHealthChecker(unittest.TestCase):

    def test_cpu_parsing(self):
        line = "cpu 100 20 30 400 10 5 5 0"

        total, idle = parse_cpu_line(line)

        self.assertEqual(total, 570)
        self.assertEqual(idle, 410)

    def test_ram_parsing(self):
        sample = """
MemTotal:       8000000 kB
MemAvailable:   3000000 kB
MemFree:        2000000 kB
"""

        result = parse_meminfo(sample)

        self.assertEqual(result["total_mb"], 7812.5)
        self.assertEqual(result["used_mb"], 4882.81)
        self.assertEqual(result["percent"], 62.5)

    def test_threshold_warning(self):
        alerts = check_thresholds(90, 50, 85)

        self.assertEqual(len(alerts), 2)

    def test_healthy_system(self):
        alerts = check_thresholds(30, 40, 50)

        self.assertEqual(alerts, [])

    def test_custom_threshold(self):
        alerts = check_thresholds(
            60, 40, 30,
            cpu_limit=50,
            ram_limit=80,
            disk_limit=80
        )

        self.assertEqual(len(alerts), 1)


if __name__ == "__main__":
    unittest.main()