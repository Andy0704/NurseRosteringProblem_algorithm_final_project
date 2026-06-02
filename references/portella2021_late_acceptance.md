# Portella (2021) — Late Acceptance Fix-and-Optimize (LAFO)

**Citation:** Portella, V.S. (2021). Mathematical Models and a Late Acceptance
Fix-and-Optimize Approach for a Nurse Rostering Problem. Master's thesis,
PPGC–UFRGS, Porto Alegre.

**Problem:** Static version of INRC-II (all weeks solved at once).

---

## Late Acceptance List Size $\gamma$

$$\boxed{\gamma = 150}$$

Tuned by the **irace** automatic configuration package on 9 training instances
(IDs 1, 4, 8, 11, 14, 18, 21, 24, 28 from the INRC-II hidden set, covering
small/medium/large sizes). Budget: 1,000 CPLEX executions.

**Tested range:** $\{1, 20, 50, 100, 150, 200, 250, 300, 500, 700\}$.

> $\gamma = 1$ reduces LAFO to the classical F&O (accept only when improving).
> irace did **not** select $\gamma = 1$, confirming the LA mechanism provides
> essential diversification beyond standard F&O.

**Other tuned parameters:**

| Parameter | Best value | Tested range |
|---|---|---|
| Subproblem time limit $STL$ | 8 s | $\{1, 5, 8, 10, 15, 30, 60, 120\}$ s |
| Neighbourhood coverage $\alpha$ | $\lfloor 8 - 0.06n \rfloor$ % | Defined as function of $n$ (nurses) |

$\alpha$ decreases for larger instances so that the per-iteration computational
load stays bounded.

---

## Acceptance Criterion Formula

**Circular list** $L = (L_1, \ldots, L_\gamma)$, initialized at start:

$$L_i \leftarrow Z(s_0) \quad \forall\, i \in \{1, \ldots, \gamma\}$$

At each iteration $\textit{iter}$ with candidate solution $s'$:

$$i \;\leftarrow\; \textit{iter} \bmod \gamma$$

**Accept $s'$ as current solution if:**

$$\boxed{Z(s') \;<\; L_i}$$

**On acceptance, update list and incumbent:**

$$L_i \leftarrow Z(s'), \qquad s \leftarrow s'$$
$$\text{if } Z(s) < Z(s^*):\quad s^* \leftarrow s$$

$L_i$ holds the objective value of the solution that was **accepted $\gamma$
iterations ago**. Accepting $s'$ when $Z(s') < L_i$ allows temporarily accepting
solutions **worse than the current best** $s^*$, enabling escape from local optima
that standard F&O cannot leave.

---

## How LA Combines with F&O

### Decomposition: blocks of nurses × combinations of weeks

**Block** $P_b$: partition of all $N$ nurses into groups of $b$ consecutive
nurses. Block size $b$ starts at 1 and increments after all week combinations are
exhausted; wraps to 1 when $b > |N|/2$.

Each F&O sub-problem frees:
- $\mathcal{N}$: one 2-combination drawn from $P_b$ (a pair of nurse blocks)
- $\mathcal{W}$: one $k$-combination of weeks, $k \in \{1, \ldots, |W|\}$

### Full LAFO Algorithm (Figure 4.1 in thesis)

```
LAFO(TL, STL, α, γ):
  s  ← solve(hard constraints only)    # initial feasible solution
  s* ← s
  for i ∈ 1..γ: L_i ← Z(s)           # initialize circular list
  iter ← 0
  b    ← 1                             # starting block size
  W    ← {1, ..., |D|/7}              # full week index set

  repeat until elapsed time ≥ TL:
    for k ∈ 1..|W|:                   # k = number of weeks to unfix
      for W ∈ random-permutation( C(W, k) ):   # all k-subsets of W
        for N ∈ α%-sample( C(P_b, 2) ):        # α% of nurse-pair combos
          s' ← solve(s, STL, W, N)             # MIP sub-problem
          i  ← iter mod γ
          if Z(s') < L_i:
            L_i ← Z(s')
            s   ← s'
            if Z(s) < Z(s*):  s* ← s
          iter ← iter + 1
    b ← b + 1
    if b > |N| / 2:  b ← 1

  return s*
```

### solve(s, STL, W, N) internals

1. **Fix** $x_{ndsk} = \bar{x}_{ndsk}$ for all nurses **not in** $\mathcal{N}$
   and all days **not belonging to weeks in** $\mathcal{W}$.
2. **Free** all $x_{ndsk}$ where $n \in \mathcal{N}$ and $d$ falls within $\mathcal{W}$.
3. Call CPLEX with time limit $STL$.
4. If a feasible solution is found within $STL$: return it. Otherwise: return
   the previous current solution $s$ (no change).

### Why LA is necessary for F&O

Standard F&O uses **greedy acceptance** (line 8 of Algorithm 3: accept only if
`Cost(S') < Cost(S)`). This causes premature convergence to the first local optimum
reachable from the initial solution.

The LA criterion provides a **memory-based escape mechanism**:
- $L_i$ remembers the cost from $\gamma$ iterations ago.
- If the search has been in a plateau or degenerating region for $\gamma$ steps,
  $L_i$ will be higher than the current level, relaxing the acceptance bar.
- This allows the algorithm to **move uphill temporarily** without explicit
  temperature control.

From Fig. 5.1 (convergence curves for small/medium/large instances with $\gamma=150$):
significant gap **oscillations in the first 30 minutes** are visible — this is the
LA diversification phase actively accepting worse solutions before converging.

---

## Experimental Results Summary (Table 5.5 vs Wickert et al. 2016 F&O)

| Instance group | F&O avg gap | LAFO avg gap | Improvement |
|---|---|---|---|
| Small (35 nurses, 10 instances) | 11.7 % | 10.2 % | −1.5 pp |
| Medium (70 nurses, 10 instances) | 21.2 % | 15.9 % | −5.3 pp |
| Large (110 nurses, 10 instances) | 32.0 % | 25.6 % | −6.4 pp |
| **All 30 instances** | **21.7 %** | **17.3 %** | **−4.4 pp** |

Coefficient of variation across 10 runs: **2 %** (highly reproducible).

LAFO outperforms F&O on 25 of 30 instances. The performance gap grows with
instance size, suggesting LA diversification is increasingly important as the
search space expands.
