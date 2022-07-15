"""
RECURSIVE CROSSWORDLE SOLVER:

This program is a solver for puzzles at crosswordle.vercel.app.

Designed to be a pythonic extension to the official crosswordle (V1) checker - the ability to force tile values will be added later as it is a V2 feature,
it contains all of the same behaviours, but, as a separate python project, allows for finer-controlled customization.

example customizations include:
   using the full word list instead of the official crosswordle checker's list of common words.
   obtaining an array containing all solutions rather than crosswordle's single solutions selected at random
   using the list of colourings to specify a puzzle of a length which the crosswordle checker will not allow (e.g.: 2 rows or >6 rows)

Execution for the solver occurs in two main steps, approximately as follows:

1. Generate colour hash table (or load it from an external file)

The hash table is in the form:
table[(solution, colouring)] = [guesses that can give that colouring]

Using this table serves as a way of skipping having to loop over the wordlist when checking colour possibilities.

2. Recursive backtracker

The solver runs as a recursive backtracking algorithm.

The inputs are the set of colours for the entire puzzle and the possible initial conditions (inputs for the bottom row of the puzzle).

From these, the backtracker repeatedly extends the puzzle by one row, obtaining all options for such an extension as initial conditions for the next row.

The process of extension goes as follows:
Use the lookup table to find words that may fill the colouring for the next row up. These are then filtered via the rules:
     i) A letter which has appeared on a grey tile in a previous row cannot reappear on a grey tile in this row.
     ii) A letter which appears on a yellow *or* grey tile cannot be above a location where it was placed in a previous row.
     iii) The yellows and greens in this row must be a sublist (i.e.: sequence of items chosen from) the yellows and greens in the previous row.
     (note that, for efficiency, if we find 2 words work, we may discard the colouring immediately)
"""

# imports for our program
import random, itertools, pickle, os

# NYT wordle answer list ("common words")
with open("wordles.txt") as f:
    WORDLES = f.read().split(", ")

# NYT wordle guess list (any word you can enter into a crosswordle row will be in here)
with open("extendedwordles.txt") as f:
    EXTENDED_WORDLE = f.read().split(", ")

# ====================================== BASIC SCRIPTS ===================================== #
# this part of the code is a few basic scripts that are common for any form of wordle variant search.

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

# function for generating a hash table allowing O(1) lookup of all words that satisfy a given colouring under a given solution
def get_table(words, ext_words):
    table = {}
    for i, sol in enumerate(ext_words):
        if i % 100 == 0: print(i) # this print statement is so a person using the program knows it's not just hanging.
        for guess in ext_words:
            if sol != guess:
                # get the decimal representation of the (ternary) wordle colouring.
                coln = ternarytonum(wordle_colour(guess, sol))
                # store in the format table[(sol, coln)] = [list of guess words that would work] 
                if (sol, coln) in table.keys():
                    table[(sol, coln)].append(guess)
                else:
                    table[(sol, coln)] = [guess]
    return table

# function for getting the (ternary) wordle colouring of a guess under a given solution.
# Green = 2, Yellow = 1, Grey = 0.
def wordle_colour(guess, solution):
    col = [0, 0, 0, 0, 0]
    observed = []
    for pos, letter in enumerate(solution):
        if guess[pos] == solution[pos]:
            col[pos] = 2
        else: observed.append(letter)

    for pos, letter in enumerate(guess):
        if letter in observed and col[pos] != 2:
            observed.remove(letter)
            if solution[pos] != letter:
                col[pos] = 1

    return col

# utility function for saving a hashtable to a local file
def save_hashtable(table, filename):
    with open(filename, 'wb') as fp:
        pickle.dump(table, fp, protocol=pickle.HIGHEST_PROTOCOL)

# utility function for loading hashtables from a local file
def load_hashtable(filename):
    with open(filename, "rb") as fp:
        return pickle.load(fp)

# utility function for saving puzzles to a local file
def save_puzzles(puzzles, filename):
    with open(filename, "w") as f:
        s = []
        for (words, nums) in puzzles:
            s.append("|".join(map(lambda il: ",".join(str(i) for i in il), [words, nums])))
        f.write("\n".join(i for i in s))

# ===================================== PUZZLE FINDING ===================================== #
# the parts of the script used to find forced puzzles

# bootstrap function used to find all puzzles on a given word list of a given length
def find_all_puzzles(wordlist, numrows):
    puzzles = []
    print("preprocessing step: finding valid colourings")
    good_colours = find_good_colours(numrows)
    for n, word in enumerate(wordlist):
        print(f"solving word {n+1} of {len(wordlist)}")
        puzzles += find_puzzles([word], numrows, good_colours)
    return puzzles

# function call for finding puzzles with unique solutions.
# takes a list of possibilities for the bottom row (for this project that's just [word] for whatever word goes there)
# number of rows and the list of good colourings on those rows.
def find_puzzles(wordlist, numrows, good_colours):
    results = []
    c = 0
    # for each colouring, run the recursive backtracking solver. if a unique solution is found for the colouring, save it.
    for col in good_colours:
        #if (c+1) % 100 == 0: print(f"{c+1} of {len(good_colours)}")
        c += 1
        nums = [242] + list(col)
        result = solve_function(wordlist, nums, table)
        if result: results.append((nums, result[0]))
    return results

# utility function for finding all good colours of a given length.
def find_good_colours(numrows):
    combos = itertools.product([i for i in range(0, 242)], repeat=numrows-1) # every possible way of choosing N-1 numbers (0-242)
    good_cols = []
    for col in combos:
        if is_valid(col):
            good_cols.append(col)
    return good_cols

# utility function for checking if a given colour combination is valid.
def is_valid(cols):
    prev_col = [2,2,2,2,2]
    prev_num = 999999
    visited = [242]
    for num in cols:
        current_col = numtoternary(num)
        
        # green cannot go above green
        for i, c in enumerate(current_col):
            if c == 2 and prev_col[i] != 2: return False
            
        # number of non-grey must be <= prev number of non-grey
        current_num = sum(map(lambda x: x > 0, current_col))
        if current_num > prev_num: return False
        
        # no duplicate rows
        if num in visited: return False

        visited.append(num)
        prev_num = current_num
        prev_col = current_col
        
    return True

# ==================================== RECURSIVE SOLVER ==================================== #
# the recursive backtracking solver used to find puzzle solutions.

# a bit of a more front-end friendly function for the recursive backtracker to use:
# takes the options for the bottom row, colour numbers, and the hash table
# then calls a recursive backtracker on the result.
# returns [[words]] if a unique solution exists, None otherwise.
def solve_function(options, nums, table):
    res = recursive_backtracker([], options, nums, table)
    if res: return res

# recursive backtracking solver
# returns:
#    [[words]] if a unique set of words exists that works for the colours given
#    None if no solution is found
#    False if more than one solution is found
def recursive_backtracker(selected, options, nums, table):
    solutions = []

    # if we have reached the target length with options left to play in that position, we may have a solution.
    if len(selected) == (len(nums)-1) and len(options) > 0:
        # attempt to play each option.
        greys = get_greys(selected, nums)
        for option in options:
            # if the option obeys hardmode, we have a solution.
            if obeys_hardmode(option, selected, nums, greys, table):
                if len(solutions) == 0: solutions = [selected + [option]]
                else: return False
        if solutions != []: return solutions
        else: return None

    # in the case where we do not have enough rows yet, we make it past the above clause, and attempt playing any options we have.
    for i, word in enumerate(options):
        greys = get_greys(selected, nums)
        
        # if the option we could play obeys hardmode
        if obeys_hardmode(word, selected, nums, greys, table):
            entry = selected+[word]
            
            # and the colouring for the next row has any options that can be played in it at all (edge case, prevents an error)
            if (entry[0], nums[len(selected)+1]) in table.keys():
                
                # we advance to the next row with those options as our new options, and the option we just played added to our solution.
                res = recursive_backtracker(entry, table[(entry[0], nums[len(selected)+1])], nums, table)

                if res == False: return False
                if res != None:
                    if len(solutions) > 0: return False
                    else: solutions = res

    if solutions != []:
        return solutions

# ===================================== HARDMODE CHECKS ==================================== #
# this part of the code is a collection of functions used to check wordle hardmode rules are satisfied

# function for checking if a word option obeys hardmode, given current solution words, colours, grey tile letters and a hash table.
def obeys_hardmode(option, selected, nums, greys, table):
    # bottom row always obeys hard mode
    if selected == []: return True
    else:
        # other rows require a check via the is_good_word function.
        row = len(selected)-1
        return is_good_word(option, numtoternary(nums[row+1]), greys, selected, selected[row], nums[row])

# function for checking if a word satisfies requirements to be playable on the next row in crosswordle,
# given that row's colour, the greys from all previous rows, the words from previous rows, and the previous word and previous word's colouring.
# if a word satisfies all requirements, return True, otherwise return False.
def is_good_word(word, col, greys, words, prevword, prevcoln):
    nongreys = []
    for index, letter in enumerate(word):
        if col[index] == 0:
            if letter in greys:
                # rule 1: A letter which has already been used as a grey tile in a previous row cannot be reused as a grey tile in this row.
                return False
            if aligned(letter, index, words):
                # rule 2: letters on yellow or grey tiles cannot appear above somewhere that they were placed in a previous row.
                return False
        else:
            nongreys.append(letter)
            if col[index] == 1 and aligned(letter, index, words):
                # rule 2: letters on yellow or grey tiles cannot appear above somewhere that they were placed in a previous row.
                return False
    
    prevnongreys = get_nongreys(prevword, prevcoln)

    # rule 3: yellow and green letters in this row must be a sublist of the yellow and green letters from the previous row.
    if not is_sublist(nongreys, prevnongreys):
        return False

    return True

# utility function for getting the list of all grey letters from previous guesses.
def get_greys(words, nums):
    greys = []
    for word, coln in zip(words, nums):
        for index, letter in enumerate(word):
            col = numtoternary(coln)
            # any letter on a grey tile is added to the list of grey letters.
            # (note that this includes tiles which are otherwise green/yellow,
            #  the inclusion of such letters corresponds to losing the ability to over-use the letter) 
            if col[index] == 0:
                if not letter in greys:
                    greys.append(letter)
    return greys

# utility function to check whether a letter has appeared in a given spot in any previous word.
# returns true if it has, false otherwise.
def aligned(letter, index, words):
    for word in words:
        if word[index] == letter:
            return True

    return False

# utility function for checking whether an array (sub) is a sublist of a larger array (full)
# a sublist is an array which could be constructed by removing elements from the larger array.
# e.g.: [1,2,2] is a sublist of [2,3,1,3,5,6,2], but not a sublist of [2,3,1,3,5,6] (as in that case, the 2nd 2 is missing).
def is_sublist(sub, full):
    for e in sub:
        if e in full:
            full.remove(e)
        else:
            return False
    return True

# utility function for getting all green and yellow letters from a word, given its colouring.
def get_nongreys(word, coln):
    nongreys = []
    col = numtoternary(coln)
    for index, letter in enumerate(word):
        if col[index] != 0:
            nongreys.append(letter)
    return nongreys

# ======================================== EXECUTION ======================================= #
# a simple example script which executes when this file is loaded.

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
    all_puzzles = find_all_puzzles(EXTENDED_WORDLE, 3)
    save_puzzles(all_puzzles, "unique_triples.txt")
