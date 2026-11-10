E2E Test Suite
===============

## Prerequisites

Ensure that you have the following 3 games dumped and that they match
these SHA1 hashes:

1. Pokémon Emerald, English (`f3ae088181bf583e55daf962a92bb46f4f1d07b7`)
2. Pokémon Ruby, English, Rev. 2 (`5b64eacf892920518db4ec664e62a086dd5f5bc8`)
3. Pokémon FireRed, English, Rev. 1 (`dd5945db9b930750cb39d00c84da8571feebf417`)


## Run

From **the repository root**, run one of the following commands:

```bash
# Runs all tests
python -m unittest discover -s tests
````

```bash
# Runs only tests from a particular file:
python -m unittest tests.test_mode_spin
```

```bash
# Runs a single test
python -m unittest tests.test_mode_spin.TestModeSpin.test_it_catches_shinies
```


## Testing every game and language

The `*_in_all_languages` tests use the states of
[Johnnie's Pokebot-Profiles](https://github.com/johnnieb333/Pokebot-Profiles)
(`Drop-In Profiles/Master Tests`), which cover most modes in all 5 games and
6 languages. They need the matching ROMs in `roms/` and the path of the
`Master Tests` directory in `POKEBOT_MASTER_TESTS`, otherwise they are skipped.
`POKEBOT_MASTER_TESTS_FILTER` limits them to states whose path contains some
text, like `FRA` or `JPN/Ruby`.

```bash
export POKEBOT_MASTER_TESTS="/path/to/Pokebot-Profiles/Drop-In Profiles/Master Tests"
python -m unittest tests.test_mode_starter
```

Each state runs as a sub-test. A test for a mode usually looks like this:

```python
class TestSomeMode(BotTestCase):
    @with_master_test_states("SomeMode-*.ss1", games=RSE_GAMES)
    @with_frame_timeout(20000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.modes.some_mode import SomeMode

        yield from self.run_mode(SomeMode, 3, choices=["Option to pick"], save_game=True)
```

`run_mode()` skips states where the mode can't be selected, saves in-game
first with `save_game=True` (modes that soft reset need it), picks the given
options in choice windows, and runs the mode until it has logged that many
encounters. Stopping for a shiny counts as a success.


### The English states in other languages

`POKEBOT_TEST_LANGUAGE` (`D`, `F`, `I`, `J` or `S`) runs the states of
`tests/states/` in another language. Each state is loaded in English, saved
in-game, and that save game is continued in the same game in that language
before the test starts, as save games have the same format (Japanese FR/LG
just has a shorter last section, which the tests cut). It needs those ROMs
in `roms/`. In the Safari Zone, Safari mode is left while saving and
restored afterwards.

```bash
POKEBOT_TEST_LANGUAGE=F python -m unittest tests.test_battle_evolution
```

### Running tests in parallel

The full suite takes a while in one process. `tests/runner/` runs one process
per test file and language, and has a local web page to start runs and follow
them, with each state's result and the output of each process:

```bash
python tests/runner/dashboard.py
```

Then open http://127.0.0.1:8765. Runs can also be started without it, for
example `python tests/runner/run_parallel.py my-run test_mode_spin test_mode_fishing`.
Logs go to `tests/runner/logs/`.


## Writing tests

Check out one of the existing test files for inspiration, but here are
some things to be aware of:

1. A file with test cases must match the naming pattern `test_*.py`.
2. Inside that file, create a class that inherits from `BotTestCase`.
3. This class can have an arbitrary amount of test methods, but each
   of them must have a name that starts with `test_`.
4. Make sure that any imports from `utility.py` are done with
   `from tests.utility import ...` instead of `from utility import ...`.
5. Any imports from the `modules` directory need to be done _inside the
   test method_ and not outside. This is to ensure that nothing is loaded
   before the test runner can set up its mocks.
6. For tests that require soft resets, the save game must be included
   in the state file. That is **not** the case for regular save states
   that the bot creates. To create such a save state, run the bot in
   debug mode and then use the `Debug` menu and select `Create state
   with save game`.

### A basic template

```python
from tests.utility import BotTestCase, with_save_state, with_frame_timeout

class TestWhatever(BotTestCase):
    @with_save_state("emerald/some_state.ss1")
    @with_frame_timeout(1000)
    def test_something(self): ...

    @with_save_state(["emerald/some_state.ss1", "ruby/some_state.ss1"])
    @with_frame_timeout(1500)
    def test_something_else(self):
        # This will run twice -- once with each state listed in the
        # @with_save_state decorator.
        ...
```
