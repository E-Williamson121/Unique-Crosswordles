# Unique-Crosswordles
A pythonic attempt to find crosswordle puzzles of unique solution.

As whether uniqueness includes when words can swap is debatable, two versions of the engine exist:
crosswordlefinder.py - Does not allow swaps in unique puzzles, result of running on length 3 is unique_triples.txt
swappycrosswordlefinder.py - Allows swaps in unique puzzles. Currently only considers length 3 puzzles where swaps exist. Result of running is swappy_triples.txt.

All 3-row puzzles been computed and may be analysed with the analysis script to find puzzles which are forced by single letter placements, or being told information about the bottom row (e.g.: "bottom row has a letter X, bottom row is a NYT word")

Todos: Translate this code to a faster language (i.e.: java, C++) in order to attempt to find 4-row puzzles
