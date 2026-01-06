# Testing Guide

This guide covers running tests for the Commander Pod Discord Bot.

## Test Files

- `tests/test_pod_optimizer.py` - Unit tests for pod optimization logic
- `tests/test_scheduler.py` - Unit tests for poll scheduling functionality
- `tests/test_optimizer.py` - Integration tests with example scenarios
- `tests/test_complex_scenarios.py` - **Complex pod scheduling scenarios (12 progressive tests)**
- `tests/run_tests.py` - Test runner for all unit tests
- `scripts/run_complex_tests.sh` - Quick runner for complex scenarios only

## Running Tests

### Run All Unit Tests

```bash
python tests/run_tests.py
```

This will discover and run all test files (test_*.py) with detailed output.

### Run Specific Test File

```bash
# Test pod optimizer
python -m unittest tests.test_pod_optimizer

# Test scheduler
python -m unittest tests.test_scheduler

# Test complex scheduling scenarios (recommended!)
python tests/test_complex_scenarios.py
# Or use the shell script:
./scripts/run_complex_tests.sh
```

### Run Specific Test Class

```bash
python -m unittest tests.test_pod_optimizer.TestPodOptimizer
```

### Run Specific Test Method

```bash
python -m unittest tests.test_pod_optimizer.TestPodOptimizer.test_basic_four_player_pod
```

### Run Integration Tests (Visual Output)

```bash
python tests/test_optimizer.py
```

This runs example scenarios and prints formatted results showing how the bot would respond.

### Run Complex Scheduling Scenarios

```bash
python tests/test_complex_scenarios.py
```

This runs 12 progressively complex pod scheduling scenarios with detailed output for each.

## Test Coverage

### Pod Optimizer Tests (`tests/test_pod_optimizer.py`)

- ✅ Basic 4-player pod formation
- ✅ Insufficient players (< 4)
- ✅ Multiple pods on same day
- ✅ Pods across multiple days
- ✅ Players available multiple days
- ✅ 5 players (one left out)
- ✅ No availability
- ✅ Choice scenario detection
- ✅ Result formatting
- ✅ Helper functions

### Scheduler Tests (`tests/test_scheduler.py`)

- ✅ Scheduler initialization
- ✅ Poll job creation
- ✅ Cutoff job creation
- ✅ Cron trigger configuration
- ✅ Timezone handling
- ✅ Different timezones
- ✅ Job execution
- ✅ Scheduler lifecycle (start/stop)
- ✅ Replace existing jobs
- ✅ Missing timezone defaults
- ✅ Invalid timezone handling

### Complex Scheduling Scenarios (`tests/test_complex_scenarios.py`)

12 progressively complex scenarios testing pod assignment logic:

1. **Simple Two Days** - 4 players Mon, 4 different Wed (no overlap)
2. **One Overlap Player** - Player available both days, can fill either slot
3. **Critical Overlap** - Player needed for both pods (choice scenario)
4. **Multiple Overlaps** - Many players with multiple availabilities
5. **Uneven Distribution** - 8 players Mon, 2 players Tue
6. **Three Days Complex** - Overlapping availability across 3 days
7. **Super Flexible Player** - One player available all 3 days
8. **Exact Multiples** - Perfect 4 players each day
9. **Barely Short** - All days have exactly 3 players (no pods form)
10. **Everyone Flexible** - All 8 players available all days
11. **Bridge Player** - One player connects two partial groups
12. **Cascading Priorities** - 16 players with overflow management

## Verbose Output

For more detailed test output:

```bash
python -m unittest tests.test_pod_optimizer -v
```

## Testing Best Practices

### Before Committing

Run all tests to ensure nothing is broken:
```bash
python tests/run_tests.py
```

### Testing New Features

1. Write tests first (TDD approach)
2. Run tests to see them fail
3. Implement the feature
4. Run tests to see them pass

### Manual Testing with Discord

After unit tests pass, test with Discord:

1. Start bot: `python run.py`
2. Create test poll: `!createpoll`
3. Vote with multiple accounts
4. Calculate pods: `!calculatepods`

### Common Test Patterns

**Testing async functions:**
```python
import asyncio

def test_async_function(self):
    async def run_test():
        result = await some_async_function()
        self.assertEqual(result, expected)

    asyncio.run(run_test())
```

**Mocking Discord objects:**
```python
from unittest.mock import Mock

mock_channel = Mock()
mock_channel.id = 123456789
mock_channel.send = AsyncMock()
```

## Continuous Integration

To add CI/CD, create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python tests/run_tests.py
```

## Debugging Failed Tests

### Get more information:
```bash
python -m unittest test_file.py -v --locals
```

### Run with Python debugger:
```python
import pdb; pdb.set_trace()  # Add to test
python -m unittest test_file.py
```

### Check specific assertion:
```python
def test_something(self):
    result = function_to_test()
    print(f"Result: {result}")  # Debug output
    self.assertEqual(result, expected)
```

## Future Test Additions

Consider adding tests for:
- Discord API error handling
- Network failures
- Database persistence (if added)
- User permission edge cases
- Poll expiration handling
- Concurrent poll scenarios

## Test Maintenance

- Update tests when features change
- Remove tests for deprecated features
- Keep test data realistic
- Document complex test scenarios
- Regularly review test coverage
