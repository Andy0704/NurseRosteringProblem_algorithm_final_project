# Knust & Xie (2019) — SA Operators and Delta Evaluation

**Citation:** Knust, F. & Xie, L. (2019). Simulated annealing approach to nurse
rostering benchmark and real-world instances. *Ann. Oper. Res.* 272, 187–216.

---

## TwoWaySwap Operator — Exact Steps

1. Draw two nurses $n_1, n_2$ uniformly at random from $\mathcal{N}$.
2. Draw one day $d$ uniformly at random from $\mathcal{D}$.
3. Swap assignments: let $a_1 = \text{activity}(n_1, d)$, $a_2 = \text{activity}(n_2, d)$.
   Set $\text{activity}(n_1, d) \leftarrow a_2$ and $\text{activity}(n_2, d) \leftarrow a_1$.
4. With 50 % probability, execute one additional independent TwoWaySwap
   (re-draw $n_1, n_2, d$ independently).

> The operator **only exchanges** activities between nurses; the total count of
> assignments per shift type per day is preserved, so coverage penalties can only
> change if the swapped nurses belong to different qualification groups.

**Penalty terms that may change:**

| Term | Why it changes |
|------|---------------|
| Coverage / shift-group coverage ($c^{\min}_{r,s}$, $c^{\max}_{r,s}$) | Only if nurses have different skill qualifications |
| Arc costs $C^A_a$ for arcs incident to $(n_1, d)$ and $(n_2, d)$ | Incoming arc $(d{-}1 \to d)$ and outgoing arc $(d \to d{+}1)$ for both nurses |
| Sequence penalties $\omega^{\min}$/$\omega^{\max}$ at days $d{-}1, d, d{+}1$ | Forbidden-successor check on the two boundary arcs per nurse |
| Weekly working-hours penalty $e^+_{r,w,n}$, $e^-_{r,w,n}$ | If the swapped activities have different durations $H_s$ |
| Preference violations (arc costs) | If the newly assigned activity violates a nurse's preference |

Terms that **do not** change: every other nurse's entire schedule, every other day's
coverage, working-time of weeks not containing $d$.

---

## RandomMove Operators — Exact Steps

### RandomSwap
1. Draw nurse $n$ uniformly at random.
2. Draw day $d$ uniformly at random.
3. Draw a new activity $a'$ uniformly from the set of activities reachable from
   $(n, d{-}1)$ via the nurse's arc-set, **excluding** the current activity.
4. Assign $\text{activity}(n, d) \leftarrow a'$.

**Used when:** coverage of a shift type needs correcting (TwoWaySwap preserves
activity counts, so it cannot fix overcoverage/undercoverage on its own).

### DayOff (specialised RandomSwap)
Same as RandomSwap but step 3 is fixed: $a' \leftarrow \text{DayOff activity}$.

**Used when:** a specific shift is overcovered; DayOff is selected with certainty
rather than relying on RandomSwap's low natural probability of choosing DayOff.

---

## Delta Evaluation

### Why O(N·D) full recalculation is wasteful

The objective function (equations 11–19 in the paper) sums arc costs and penalty
violations over **all** nurses and **all** days:

$$Z = \underbrace{\sum_{a \in \mathcal{A}} x_a C^A_a}_{\text{arc costs}}
    + \sum_{r} \sum_{n \in N_r} \sum_{d \in D} \text{violation}(r, n, d)$$

A naïve re-evaluation after each move costs $\mathcal{O}(N \cdot D)$.

### O(1) delta update for TwoWaySwap on day $d$

Only arcs and constraints touching the two affected nurses on days $d{-}1, d, d{+}1$
need to be re-evaluated. Let $\delta Z = Z_{\text{new}} - Z_{\text{old}}$:

$$\delta Z =
  \underbrace{\Delta C^A_{n_1,\,d-1\to d} + \Delta C^A_{n_1,\,d\to d+1}}_{\text{arc costs } n_1}
+ \underbrace{\Delta C^A_{n_2,\,d-1\to d} + \Delta C^A_{n_2,\,d\to d+1}}_{\text{arc costs } n_2}
+ \underbrace{\Delta \mathrm{cov}_d}_{\text{coverage, day } d}
+ \underbrace{\Delta \mathrm{seq}_{n_1,d} + \Delta \mathrm{seq}_{n_2,d}}_{\text{sequence penalties}}
+ \underbrace{\Delta H_{n_1,w} + \Delta H_{n_2,w}}_{\text{hours penalty, week } w}$$

| Component | Cost |
|---|---|
| 4 arcs re-evaluated (2 per nurse × 2 boundary transitions) | $\mathcal{O}(1)$ |
| Coverage for 1 day ($\|\text{shifts}\| \times \|\text{skills}\|$ terms) | $\mathcal{O}(1)$ |
| 2 sequence windows of length 2 (one per nurse) | $\mathcal{O}(1)$ |
| 2 weekly-hours updates (one per nurse) | $\mathcal{O}(1)$ |
| **Total** | **$\mathcal{O}(1)$ vs $\mathcal{O}(N \cdot D)$** |

This means neighbouhood evaluation cost is **constant regardless of instance size**.
For a 50-nurse × 28-day instance, the delta skips ~1,400 unnecessary evaluations
per SA iteration.

For **RandomSwap** of nurse $n$ on day $d$: same formula with $n_2$ terms dropped
(only one nurse changes). For **SwapSequences** of length $\ell$: sum $\delta Z$
over $\ell$ consecutive days × 2 nurses — still $\mathcal{O}(\ell)$ ≈ $\mathcal{O}(1)$
since $\ell \leq 6$.

---

## SA Parameters (Section 5.3)

### Initial Temperature

Computed **dynamically per instance** to ensure ~50 % acceptance probability
at the start of the hot phase:

$$T_0 = \text{multiplier} \times \max_{n,\, a}\!\left[\sum_{\substack{r \,:\, n \in N_r \\ a \in S_r}} C^R_r \;+\; C^A_{a,n}\right]$$

- Inner $\max$ = maximum single-swap objective degradation = worst-case sum of
  penalty weights for all constraints involving one nurse–activity combination,
  plus the maximum arc cost for that nurse.
- **multiplier** tuned over $\{5, 10, 15, 20, 25, 30\}$; **best = 20**
  (validated on GPost, KHStation6-April, WohnbereichGelb-April, KHIntensiv;
  30 runs each).

### Cooling Schedule (Geometric)

$$T_{k+1} = \beta \cdot T_k \quad \text{every } 30{,}000 \text{ SA iterations}$$

- **Cooling factor** $\beta$ tuned over $(0.5, 0.9)$; **best = 0.9**
  (0.9 yields best average quality at cost of longest runtime).
- Termination conditions (whichever occurs first):
  1. $T < 10$ (temperature lower bound)
  2. No improving solution found for $500{,}000$ consecutive iterations

### Operator Probabilities (Section 5.2)

| Operator | Probability | Success rate |
|---|---|---|
| TwoWaySwap | 30 % | ~20 % (highest) |
| SwapSequences (lengths 2–6, 8 % each) | 40 % total | avg ~20 % |
| ThreeWaySwap | 10 % | ~15 % (lowest) |
| RandomSwap | 15 % | — |
| DayOff | 5 % | — |
