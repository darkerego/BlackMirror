
import bisect
imbalance = 0
i = 0
j = 0
groups = []

ranks=[4,1,3,2]

from itertools import combinations, cycle

char_cyc = cycle([4,1,3,2])
combos = combinations(range(8), 4)

perms = (['*' if i in combo else next(char_cyc) for i in range(8)]
         for combo in combos)

print(list(perms))