# Turhan & Bilgen (2020) — SA Parameters and Fix-and-Optimize

**Citation:** Turhan, A.M. & Bilgen, B. (2020). A hybrid fix-and-optimize and
simulated annealing approaches for nurse rostering problem. *Computers &
Industrial Engineering* 145, 106531.

---

## SA Algorithm Skeleton (Algorithm 2)

```
Initialize T₀, T_min, β, I_max, J_max
T ← T₀;  S* ← S (initial solution from F&R);  j ← 0

while T_min < T do
    i ← 0
    while i < I_max do
        k  ← Random()                   # select neighbourhood uniformly
        S' ← Generate(S, N_k)           # generate candidate
        if Cost(S') < Cost(S):
            S ← S'
        else:
            Δ ← Cost(S') − Cost(S)
            if Random(0,1) < exp(−Δ/T):  # Metropolis acceptance
                S ← S'
        if S' < S*:
            S* ← S'
        else:
            j ← j + 1
        if j ≥ J_max:
            S ← FixAndOptimize(S)        # F&O injection point
            j ← 0
        i ← i + 1
    end while
    T ← T × β                            # geometric cooling step
end while
return S*
```

---

## Initial Temperature

From parameter tuning (Fig. 8, Section 4.2):

$$\boxed{T_0 = 10}$$

Tested range: $\{1, 2, 3, 4, 5, 6, 7, 8, 9, 10\}$ (x-axis = decomposition size
paired with starting temperature in Fig. 8).
**Starting temperature 10 provides the best result** on the benchmark instance
(Instance 8: 4-week horizon, 30 nurses).

> **Context for scaling:** The soft constraint weights are SC2 (understaffing) = 100,
> SC1 (shift on/off requests) = 1–3, SC3 (overstaffing) = 1. A temperature of 10
> gives an initial acceptance probability of $e^{-100/10} \approx 0.5$ \% for a
> single-unit understaffing violation — intentionally low, so infeasible regions
> are rarely accepted even at the start.

The **F&R heuristic** (fix-and-relax) provides the initial solution $S$ fed into SA:
- Small instances: week decomposition (WD), decomposition size 4, PTL = 15 s/week.
- Large instances: nurse decomposition (ND).

---

## Cooling Schedule

**Geometric cooling** (Algorithm 2, line 27):

$$T_{k+1} = \beta \cdot T_k$$

applied **after every $I_{\max}$ inner iterations** (one full temperature level).

- $T_{\min}$: stopping temperature; SA terminates when $T \leq T_{\min}$.
- $\beta$ (cooling rate) is set alongside $T_0$.
- **Total runtime budget: 10 minutes.** 10 % (60 s) is allocated to the F&R
  initial solution phase; the remaining 540 s are shared by SA and F&O.
- Per-subproblem time is controlled by passing a time limit to CPLEX; e.g. for
  a 4-week instance in F&R, each week sub-problem gets $\leq 15$ s.

---

## F&O Injection — Reheat Trigger Condition

The F&O heuristic is inserted into the SA loop as a **diversification mechanism**
(not a classical reheat):

```
if j ≥ J_max:
    S ← FixAndOptimize(S)
    j ← 0
```

- $j$ counts consecutive SA iterations with **no improvement** to $S^*$
  (the global best), not just non-improving Metropolis-accepted moves.
- When $j = J_{\max}$, the current working solution $S$ is handed to F&O.
- After F&O returns (better or worse), $j$ is reset to 0 and SA resumes.
- **Key insight from Section 3:** even when F&O produces a worse solution, the
  perturbation diversifies the search landscape for subsequent SA moves, leading
  to better overall performance than SA alone.

From Fig. 8 (stand-alone F&O vs stand-alone SA performance):
- Stand-alone F&O stalls around 20 % gap.
- Stand-alone SA achieves steady improvements.
- **Combined SA + F&O** achieves the best final gap, confirming complementarity.

---

## Fix-and-Optimize: Selection Strategy and Decomposition

### Decomposition type inside SA loop

**Day Decomposition (DD)** — the planning horizon is split by days.

### Algorithm 3 (F&O pseudocode)

```
Input: current solution S, day decomposition P_DD
S* ← S
x_F ← Update(x_idt)             # fix ALL variables to current S values

for p in P_DD:                   # iterate over day sub-problems
    Clear(x_T)                   # clear "to-be-optimized" set for this p
    (status, S') ← Solve(p)      # call CPLEX on the sub-problem
    if status == feasible:
        if Cost(S') < Cost(S):
            S* ← S'
            x_F ← Update(x_O)   # extend fixed set with newly optimized vars
        else:
            Restore(x_T)         # revert: sub-problem worsened, undo
return S*
```

### How many days are unfixed

Controlled by the DD **decomposition size** parameter:
- From Fig. 8: larger sub-problems (more unfixed days) produce better solutions
  when time allows — quality improves monotonically with decomposition size.
- In practice, the number is bounded by the per-subproblem CPLEX time limit
  (implicitly set so that the full F&O call fits within the SA J_max budget).

### Selection strategy for unfixed days

Selection is **cost-weighted random** (not uniform random):

$$P(\text{day } d \text{ selected for optimization}) \propto \text{cost}(d)$$

Concretely:
1. Compute the objective contribution of each day $d$ in the current solution.
2. **Fix low-cost days** to their current assignment (they are near-optimal).
3. For the remaining **high-cost days**, draw the optimization subset using
   probabilities proportional to each day's cost.

**Example (from Section 3):** if Monday has 4× the cost of Tuesday, the random
generator selects Monday with 4× higher probability than Tuesday.

This ensures the F&O sub-problem focuses computational effort on the most
violated days rather than wasting solver time on already-good portions of the
schedule.

**Subproblem solver:** IBM ILOG CPLEX 12.6, default parameters, single core.

---

## Neighbourhood Structures Used in SA (Section 3.1)

| Name | Description |
|---|---|
| 2-Exchange | Swap shifts of 2 random nurses on 1 random day |
| 3-Exchange | Swap shifts of 3 random nurses on 1 random day |
| Double-Exchange | Swap 2 random nurses on 2 random consecutive days |
| Multi-Exchange | Swap 2 random nurses on 3–6 random non-consecutive days |
| Block-Exchange | Swap 2 random nurses on 3–6 random consecutive days |
| Shift-Switch | Change 1 nurse's shift to a different shift on 1 random day |
| Shift-Off | Remove 1 nurse's shift on 1 random day (assign day-off) |
| Shift-On | Assign a new shift to a free slot for 1 random nurse |

All 8 neighbourhoods are selected uniformly at random in each SA iteration.
