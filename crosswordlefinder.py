"""
UNIQUE CROSSWORDLE FINDER:

Some crosswordle puzzles can have one solution. Such puzzles have unique rows all the way up (ergo different words in each row).

This program is written to find unique crosswordles of a given length (although currently only length 3 is feasible on the full word list).
The procedure is essentially as follows:

1. Generate a large hash table of which words may be played when the solution and colouring of a row are given. These are in the form
Table[(sol, col)] = [words]

(Hard mode rules are situational depending on what is played, and so not considered by this table)

2. Generate a list of all possible valid colourings on the given length. In this context, valid colourings have the following properties:
 - rows are all different (matching rows would be non-unique as the words in those rows could be swapped.)
 - green tiles are only placed above green tiles in the previous row
 - the number of non-grey tiles must be decreasing as one ascends the puzzle.

(On length 3, ~12,000 puzzles satisfy these rules)

3. For each possible starting word, for each colouring which is valid,
   run a recursive backtracker process on the puzzle with that starting word and colouring
 - The backtracker will be given the fixed starting word and will play obeying hard mode rules to solve the puzzle.
 - If it finds more than one solution it will return False. if it finds no solution it will return None, otherwise it will return the solution it found.
 If a solution is found, we save it.

Using the statistic of Info (green tile = +2, yellow tile = +1, grey tile = +0, bottom row excluded), we get the following comparison between
the row-wise forced puzzles produced by earlier efforts and the unique puzzles produced by this search.
We may also add the "swappy puzzles" produced by later efforts to this list.

Numbers of puzzles which stick to the NYT wordlist are included in brackets for the last two columns

Info  | Forced Puzzles  | Unique Puzzles     | Swappable puzzles |
______|_________________|____________________|___________________|
2     | 0               | 4         (0)      | 0      (0)        |
3     | 43              | 297       (17)     | 0      (0)        |
4     | 582             | 5,791     (143)    | 2,027  (61)       |
5     | 7,372           | 35,011    (946)    | 0      (0)        |
6     | 30,753          | 109,569   (3,210)  | 7,449  (165)      |
7     | 105,234         | 297,354   (9,026)  | 0      (0)        |
8     | 198,335         | 406,748   (13,303) | 14,769 (444)      |
9     | 234,701         | 409,583   (13,697) | 0      (0)        |
10    | 206,647         | 298,482   (9,813)  | 2,689  (93)       |
11    | 173,240         | 215,421   (6,704)  | 0      (0)        |
12    | 143,330         | 164,137   (5,457)  | 8,340  (431)      |
13    | 86,116          | 98,298    (3,623)  | 0      (0)        |
14    | 28,946          | 33,244    (1,385)  | 48     (1)        |
15    | 5,656           | 6,766     (294)    | 0      (0)        |
16    | 0               | 0         (0)      | 7,962  (565)      |
______|_________________|____________________|___________________|
total | 1,220,955       | 2,080,705 (67,618) | 43,284 (1,760)    |

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
        if result: results.append((result[0], nums))
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
        
        # green must go above green
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
