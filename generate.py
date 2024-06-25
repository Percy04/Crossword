import sys
import pprint
from crossword import *
import queue

class CrosswordCreator():

    def __init__(self, crossword):

        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):

        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):

        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):

        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):

        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):

        for var in self.domains:
            domain = self.domains[var].copy()
            for words in domain:
                length = var.length
                if (len(words) != length):
                    self.domains[var].remove(words)


    def revise(self, x, y):

        changes = False
        if (self.crossword.overlaps[x,y] is not None):
            point = self.crossword.overlaps[x,y]
            # print("The point is ", end=" ")
            # print(point)
            x_index = point[0]
            y_index = point[1]
            
            check = 0
            container = self.domains[x].copy()
            for word in container:
                for more_word in self.domains[y]:
                    if (word == more_word): continue

                    if (word[x_index] == more_word[y_index]):
                        check = 1
                        break

                if (check == 0):
                    self.domains[x].remove(word)  
                    changes = True
                else: 
                    check = 0

        return changes


    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        
        variables = queue.Queue()
        if arcs is not None:
            for sets in arcs:
                variables.put(sets)
        else:
            for var in self.domains:
                for more_var in self.domains:
                    if (var == more_var): continue
                    variables.put((var, more_var))

        while variables.empty() is not True:
            x,y = variables.get()

            if (self.revise(x,y)):
                if len(self.domains[x]) == 0:
                    return False
                
                for z in Crossword.neighbors(self.crossword, x) - {y}:
                    variables.put((z,x))
                    
        return True


    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for var in self.domains:
            if (var not in assignment):
                return False

        return True


    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        for var in assignment:
            # check length
            if (var.length != len(assignment[var])):
                # print("length")
                return False

            
            for more_var in assignment:
                if (var == more_var):
                    continue

                # check duplicates
                if (assignment[var] == assignment[more_var]):
                    print("dupes")
                    return False
                
                # check neighbour constraints
                overlap = self.crossword.overlaps[var, more_var] 
                if (overlap is not None):
                    if (assignment[var][overlap[0]] != assignment[more_var][overlap[1]]):
                        # print("directions")
                        return False
        
        return True
            

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """

        my_list = list()
        # my_dict = dict()

        for words in self.domains[var]:
            my_list.append(words)

        return sorted(my_list, reverse=True)

    def select_unassigned_variable(self, assignment):

        my_dict=  dict()

        for var in self.domains: 
            if var not in assignment:
                my_dict[var] = len(self.domains[var])
        
        # pprint.pprint(my_dict)
        smallest_value = min(my_dict.values())
        keys_with_sv = [key for key,value in my_dict.items() if value == smallest_value]

        if (len(keys_with_sv) == 1):
            # print(f"yes + {keys_with_sv[0]}")
            return keys_with_sv[0]
        else:
            smallest = self.crossword.neighbors(keys_with_sv[0])
            key = keys_with_sv[0] 
            for keys in keys_with_sv:
                if self.crossword.neighbors(keys) > smallest:
                    smallest = self.crossword.neighbors(keys)
                    key = keys
        
        return key




    def backtrack(self, assignment):
        if self.assignment_complete(assignment):
            return assignment
        
        var = self.select_unassigned_variable(assignment)
        # print(var)

        for value in self.order_domain_values(var, assignment):
            # print(value)
            assignment[var] = value
            if self.consistent(assignment):
                # print("true")
                result = self.backtrack(assignment)
                if result is not False:
                    return result
            else:
                del assignment[var]

        return None 


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    creator.enforce_node_consistency()
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
