"""
UNIQUE CROSSWORDLE FINDER: ANALYSIS

This script contains various functions which are useful to the analysis of unique crosswordle puzzles.
The main scripts are:
  - Finding puzzles forced by single letters, requirement of a given letter being in the bottom row, or that the bottom row is a NYT word.
  - Saving/Loading puzzles of these types
  - Bucketing normal puzzles by Info (and other stats)
  - methods for displaying puzzles of each type
"""

import random, itertools, pickle, os
import crosswordlefinder as unique
import swappycrosswordlefinder as swappy

# NYT wordle answer list ("common words")
with open("wordles.txt") as f:
    WORDLES = f.read().split(", ")

# NYT wordle guess list (any word you can enter into a crosswordle row will be in here)
with open("extendedwordles.txt") as f:
    EXTENDED_WORDLE = f.read().split(", ")

# ============================================= BASIC FUNCTIONALITY ===================================== #

# utility function for converting a ternary list, e.g. [2, 2, 1, 2, 0], to a decimal number e.g. 231.
def ternarytonum(t):
    num = 0
    for power, n in enumerate(t[::-1]):
        num += n*(3**power)
    return num

# utility function for converting a decimal number e.g. 134 to a ternary list e.g. [1, 1, 2, 2, 2].
def numtoternary(x):
    nums = []
    while x > 0:
        x, r = divmod(x, 3)
        nums.append(r)
    while len(nums) < 5: nums.append(0)
    return nums[::-1]

# utility function for saving a hashtable to a local file
def save_hashtable(table, filename):
    with open(filename, 'wb') as fp:
        pickle.dump(table, fp, protocol=pickle.HIGHEST_PROTOCOL)

# utility function for loading hashtables from a local file
def load_hashtable(filename):
    with open(filename, "rb") as fp:
        return pickle.load(fp)

# ============================================= SAVE/LOAD FUNCTIONS: ==================================== #

# method for saving puzzles forced by knowing a letter is somewhere in the bottom row
def save_full_forces(filename, forces):
    with open(filename, "w") as f:
        s = []
        for force in forces:
            puzzle, letter = force
            words, nums = puzzle
            s.append("|".join(map(lambda il: ",".join(str(i) for i in il), [words, nums, [letter]])))
        f.write("\n".join(i for i in s))

# method for loading puzzles forced by knowing a letter is somewhere in the bottom row
def load_full_forces(filename):
    forces = []
    with open(filename) as f:
        for i, line in enumerate(f.readlines()):
            wordstr, numstr, force = tuple(line.split("|"))
            words = wordstr.split(",")
            nums = list(map(int, numstr.split(",")))
            forces.append(((words, nums), force[0]))
    return forces

# method for saving puzzles forced by a single given letter
def save_single_letter_forces(filename, forces):
    with open(filename, "w") as f:
        s = []
        for force in forces:
            puzzle, letter, pos = force
            words, nums = puzzle
            s.append("|".join(map(lambda il: ",".join(str(i) for i in il), [words, nums, [letter,pos]])))
        f.write("\n".join(i for i in s))

# method for loading puzzles forced by a single given letter
def load_single_letter_forces(filename):
    forces = []
    with open(filename) as f:
        for i, line in enumerate(f.readlines()):
            wordstr, numstr, forcestr = tuple(line.split("|"))
            words = wordstr.split(",")
            nums = list(map(int, numstr.split(",")))
            force = forcestr.split(",")
            letter = force[0]
            pos = int(force[1])
            forces.append(((words, nums), letter, pos))
    return forces

# utility function for saving puzzles to a local file
def save_puzzles(puzzles, filename):
    with open(filename, "w") as f:
        s = []
        for (words, nums) in puzzles:
            s.append("|".join(map(lambda il: ",".join(str(i) for i in il), [words, nums])))
        f.write("\n".join(i for i in s))

# utility function for loading puzzles from a local file
def load_puzzles(filename):
    puzzles = []
    with open(filename, "r") as f:
        for i, line in enumerate(f.readlines()):
            wordstr, numstr = tuple(line.split("|"))
            words = wordstr.split(",")
            nums = list(map(int, numstr.split(",")))
            puzzles.append((words, nums))
    return puzzles

# ================================= ANALYSIS FUNCTIONS: FINDING TYPED PUZZLES =========================== #

# analysis function for finding puzzles forced by a single letter in a given position.
# method is as follows: find all forced puzzles where the letter is in this position and bucket by colour.
#                       extract all unique colours within this group (bucket size 1). these are candidates for being forced
#                       for each candidate, run the solver on all words satisfying the constraint to determine if the candidate is indeed forced.
def find_single_letter_forces(all_puzzles, library):
    puzzles = []
    for letter in "abcdefghijklmnopqrstuvwxyz":
        for pos in range(0, 5):
            print(f"working on {letter}, {pos}")
            filtered_words = list(filter(lambda word: word[pos] == letter, EXTENDED_WORDLE))

            colourdict = {}
            for puzzle in all_puzzles:
                words, nums = puzzle
                if words[0] in filtered_words:
                    if tuple(nums) in colourdict.keys():
                        colourdict[tuple(nums)].append(words)
                    else:
                        colourdict[tuple(nums)] = [words]

            candidates = []
            for key in colourdict:
                if len(colourdict[key]) == 1:
                    candidates.append((colourdict[key][0], list(key)))

            for candidate in candidates:
                words, nums = candidate
                res = library.solve_function(filtered_words, nums, table)
                if res: puzzles.append((candidate, letter, pos))

    return puzzles

# analysis function for finding puzzles forced by just knowing a given letter is somewhere in the bottom row. Same method as above.
def find_full_forces(all_puzzles, library):
    puzzles = []
    for letter in "abcdefghijklmnopqrstuvwxyz":
        print(f"working on {letter}")
        filtered_words = list(filter(lambda word: letter in word, EXTENDED_WORDLE))

        colourdict = {}
        for puzzle in all_puzzles:
            words, nums = puzzle
            if words[0] in filtered_words:
                if tuple(nums) in colourdict.keys():
                    colourdict[tuple(nums)].append(words)
                else:
                    colourdict[tuple(nums)] = [words]

        candidates = []
        for key in colourdict:
            if len(colourdict[key]) == 1:
                candidates.append((colourdict[key][0], list(key)))

        for candidate in candidates:
            words, nums = candidate
            res = library.solve_function(filtered_words, nums, table)
            if res: puzzles.append((candidate, letter))

        return puzzles

# analysis function for finding puzzles forced by just knowing the bottom word is a NYT answer. Same method as above.
def find_nyt_forces(all_puzzles, library):
    puzzles = []

    colourdict = {}
    for puzzle in all_puzzles:
        words, nums = puzzle
        if words[0] in WORDLES:
            if tuple(nums) in colourdict.keys():
                colourdict[tuple(nums)].append(words)
            else:
                colourdict[tuple(nums)] = [words]

    candidates = []
    for key in colourdict:
        if len(colourdict[key]) == 1:
            candidates.append((colourdict[key][0], list(key)))

    print(len(candidates))
    for i, candidate in enumerate(candidates):
        print(f"{i+1} of {len(candidates)}")
        words, nums = candidate
        res = library.solve_function(WORDLES, nums, table)
        if res: puzzles.append(candidate)
    return puzzles

# =============================== ANALYSIS FUNCTIONS: BUCKETING PUZZLES BY STAT ========================= #
# (functions in this section were copied over from the original forced crosswordle analysis script)

# utility function for sorting a dictionary by key.
def sort_dict(mydict):
    sorted_dict = {}
    for key in sorted(mydict):
        sorted_dict[key] = mydict[key]
    return sorted_dict

# utility function for making a precomputed lookup of whether words are common or not.
# (useful because "word in WORDLES" ends up being slightly slower when used a lot)
def make_commonness_dict(ext_words, words):
    iscommon = {}
    for word in ext_words:
        iscommon[word] = word in words
    return iscommon

# utility function for taking a list of forced puzzles and filtering for puzzles that will be solvable by the crosswordle checker.
def find_common_puzzles(puzzles):
    common_puzzles = []
    for puzzle in puzzles:
        words, nums = puzzle
        if all(map(lambda x: iscommon[x], words[1:])):
            common_puzzles.append(puzzle)
    return common_puzzles

# analysis function for bucketing a list of puzzles by how many non-grey squares are in the puzzle (usually results in very yellow puzzles)
# returned are both the buckets of puzzles (number_puzzles[N] = [list of puzzles with N non-grey squares])
# and a hash table storing the size of each bucket (number_counts[N] = number of puzzles with N non-grey squares).
def bucket_puzzles_by_coln(puzzles):
    number_puzzles = {}
    number_counts = {}
    for puzzle in puzzles:
        words, nums = puzzle
        s = sum(map(lambda x: sum(map(lambda x: x > 0, numtoternary(x))), nums))
        if s in number_puzzles.keys():
            number_puzzles[s].append(puzzle)
            number_counts[s] += 1
        else:
            number_puzzles[s] = [puzzle]
            number_counts[s] = 1
    return number_puzzles, sort_dict(number_counts)

# analysis function for bucketing a list of puzzles by how much information the puzzle gives. It is assumed one green is worth two yellows.
# returned are both the buckets of puzzles (number_puzzles[N] = [list of puzzles with an information value of N])
# and a hash table storing the size of each bucket (number_counts[N] = number of puzzles with an information value of N).
def bucket_puzzles_by_info(puzzles):
    number_puzzles = {}
    number_counts = {}
    for puzzle in puzzles:
        words, nums = puzzle
        s = sum(map(lambda x: sum(numtoternary(x)), nums[1:]))
        if s in number_puzzles.keys():
            number_puzzles[s].append(puzzle)
            number_counts[s] += 1
        else:
            number_puzzles[s] = [puzzle]
            number_counts[s] = 1
    return number_puzzles, sort_dict(number_counts)

# analysis function for bucketing a list of puzzles by how many greens are in the puzzle.
# returned are both the buckets of puzzles (number_puzzles[N] = [list of puzzles with N green squares])
# and a hash table storing the size of each bucket (number_counts[N] = number of puzzles with N green squares).
def bucket_puzzles_by_greens(puzzles):
    number_puzzles = {}
    number_counts = {}
    for puzzle in puzzles:
        words, nums = puzzle
        s = sum(map(lambda x: sum(map(lambda x: x == 2, numtoternary(x))), nums))
        if s in number_puzzles.keys():
            number_puzzles[s].append(puzzle)
            number_counts[s] += 1
        else:
            number_puzzles[s] = [puzzle]
            number_counts[s] = 1
    return number_puzzles, sort_dict(number_counts)

# ============================================== DISPLAY FUNCTIONS ====================================== #

# display function for standard unique crosswordle puzzle.
def tolink(puzzle):
    words, nums = puzzle
    sol = words[0]
    print(f"https://crosswordle.vercel.app/?puzzle=v1-{','.join(str(i) for i in nums[::-1])}-{sol}")

# display function for puzzles where the puzzle is forced by knowing the bottom word has a given letter
def NYTforcetolink(puzzle):
    emptypuzzletolink(puzzle)
    print(f"the bottom word of this puzzle is a NYT answer.")

# display function for puzzles where the puzzle is forced by knowing the bottom word has a given letter
def fullforcetolink(force):
    puzzle, letter = force
    emptypuzzletolink(puzzle)
    print(f"the bottom word of this puzzle contains the letter {letter}.")

# display function for puzzles where the bottom word is empty
def emptypuzzletolink(puzzle):
    words, nums = puzzle
    sol = words[0]
    print(f"https://crosswordle.vercel.app/?puzzle=v2-{','.join(str(i) for i in nums[::-1])}-x,x,x")

# display function for puzzles where the bottom word is forced by a single given letter.
def singleforcetolink(forced_puzzle):
    puzzle, force_letter, force_pos = forced_puzzle
    words, nums = puzzle
    sol = words[0]
    print(f"https://crosswordle.vercel.app/?puzzle=v2-{','.join(str(i) for i in nums[::-1])}-x,x,{force_pos}{force_letter}")

if __name__ == "__main__":
    if os.path.exists("crosswordle_hashtable.p"):
        print("loading hash table from file")
        table = load_hashtable("crosswordle_hashtable.p")
    else:
        print("generating hash table")
        table = get_table(WORDLES, EXTENDED_WORDLE)
        print("save hashtable to local file to skip generation next time (y/n)?")
        print("(only do this if you have disk space, the file will be BIG!)")
        input()
        if k == "y":
            print("saving hash table to local file")
            save_hashtable(table, "crosswordle_hashtable.p")
