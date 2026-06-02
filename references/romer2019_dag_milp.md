# Römer & Mellouli (2019) — DAG / Network-Flow MILP

**Citation:** Römer, M. & Mellouli, T. (2016). A direct MILP approach based on
state-expanded network flows and anticipation for multi-stage nurse rostering under
uncertainty. *Proc. PATAT 2016*, pp. 549–551. *(INRC-II winners.)*

**Source note:** The reference PDF file contains the **INRC-II official problem
specification** (Ceschia et al. 2019, arXiv:1501.04177), which defines the problem
Römer & Mellouli modeled. The network architecture below is synthesized from:
- Ceschia et al. (2019) — problem constraints and forbidden succession rules
- Knust & Xie (2019) §3 — complete multi-commodity flow network implementation
  confirmed by Portella (2021) §2.3.1 to be architecturally identical to Römer's
  state-expanded network approach

---

## DAG Node Definition

Each **node** = $(s,\, d)$ — an **activity** $s \in \mathcal{S}$ on **day**
$d \in \mathcal{D}$.

**Activity set $\mathcal{S}$** contains:
- All named shift types (Early, Late, Night, Day, …)
- Day-off activity
- Standby activities (cover nurse absences)
- Pre-assigned absences (vacations, training) — included as fixed-flow nodes

Instance scale: Knust real-world data has up to 49 shift types + non-work
activities. INRC-II benchmark uses 3–10 shift types + day-off.

**Total nodes:** $|\mathcal{S}| \times |\mathcal{D}|$, shared across all nurses.

**Source and sink nodes** (one per nurse $n$):
- Dummy source $\sigma_n$ with zero-cost arcs to all activities on day 1
- Dummy sink $\tau_n$ reached from all activities on the last day

**One unit of flow** per nurse travels $\sigma_n \to \tau_n$; the chosen path
encodes the nurse's complete roster.

**Multi-commodity structure:** arcs are labelled by nurse $n$ — the arc set
$\mathcal{A}_n \subseteq \mathcal{A}$ is nurse-specific after pruning.

**Decision variable:**
$$x_a \in \{0,1\}, \quad a \in \mathcal{A}_n$$

$x_a = 1$ iff nurse $n$ traverses arc $a$ (equivalently: has the tail activity on
day $d$ and the head activity on day $d{+}1$).

**Derived assignment variable:**
$$y_{s,n} = \sum_{a \in \mathcal{B}_{s,n}} x_a = \sum_{a \in \mathcal{F}_{s,n}} x_a$$

where $\mathcal{B}_{s,n}$ (backward-star) and $\mathcal{F}_{s,n}$ (forward-star)
are the sets of arcs entering and leaving node $(s,d)$ for nurse $n$.

---

## Arc Pruning Rules for Forbidden Successions

The initial arc set contains **all possible** day-to-day transitions. Pruning
removes arcs that would always incur a hard-constraint violation, reducing the
model size before solving.

### Rule 1 — Forbidden shift-type successions (Hard constraint H3, INRC-II)

For each forbidden pair $(s_1, s_2) \in \mathcal{F}$ declared in the scenario file:

$$\text{Remove arc } (s_1,\, d) \to (s_2,\, d{+}1) \quad \forall\, d \in \mathcal{D}$$

Examples from the INRC-II spec (Appendix B):

| Forbidden succession | Reason |
|---|---|
| Late $\to$ Early | Insufficient rest time between shifts |
| Night $\to$ Early | Insufficient rest time |
| Night $\to$ Late | Insufficient rest time |

The forbidden succession matrix is defined per shift type in the scenario file:
```
FORBIDDEN_SHIFT_TYPES_SUCCESSIONS
Early 0
Late  1 Early
Night 2 Early Late
```

### Rule 2 — Nurse-contract incompatibility

For nurse $n$, remove arc $(s,\, d) \to (s',\, d{+}1)$ if:
- Activity $s$ or $s'$ requires a shift type not allowed by $n$'s contract
  (e.g., a night-shift arc for a nurse contractually excluded from nights)
- The arc would connect to a work-shift on a day that nurse $n$ has a scheduled
  absence (vacation, training — set $N_i$ for nurse $i$ in Turhan's formulation)

### Rule 3 — Pre-assigned (fixed) activities

If nurse $n$ has a fixed activity $\hat{s}$ on day $d$:
- Remove **all** incoming arcs to $(s,\, d)$ where $s \ne \hat{s}$
- Remove **all** outgoing arcs from $(s,\, d)$ where $s \ne \hat{s}$
- Retain exactly **one** arc connecting to the fixed node from the previous day's
  legal predecessor

This ensures the flow is forced through the pre-assigned activity with no
branching at that node.

Also: if the maximum consecutive working-days limit was reached at the end of the
previous period (from history), all arcs to work-related activities at the
beginning of the current period are removed.

### Rule 4 — Weekend completeness (soft, arc-cost version)

To model the complete-weekend soft constraint (S5 / INRC-II), mixed weekends
are penalised via **arc costs** rather than hard removal (Knust soft version):
- Arc `(LateFri, Fri) → (DayOff, Sat)` receives a high cost equal to the
  S5 violation weight.
- Arc `(DayOff, Sat) → (EarlyShift, Sun)` receives the same high cost.

Hard removal (forbidden-arc version) is used when complete weekends are enforced
as hard constraints.

---

## Objective Function in Network Flow Terms

$$\min\; z =
  \underbrace{\sum_{a \in \mathcal{A}} x_a \cdot C^A_a}_{\text{(11) arc / preference costs}}
+ \underbrace{\sum_{r \in \mathcal{R}^{C,\text{Soft}}} \sum_{s \in S_r}
    \!\bigl(c^{\min}_{r,s} + c^{\max}_{r,s}\bigr) C^R_r}_{\text{(12) shift-coverage violations}}
+ \underbrace{\sum_{r \in \mathcal{R}^{G,\text{Soft}}} \sum_{n \in N_r}
    \!\bigl(g^{\min}_{r,n} + g^{\max}_{r,n}\bigr) C^R_r}_{\text{(13) shift-group violations}}
+ \underbrace{\sum_{r \in \mathcal{R}^{S,\text{Soft}}} \sum_{d,n}
    v_{r,d,n}\, C^R_r}_{\text{(15) sequence / combination violations}}
+ \underbrace{\sum_{r \in \mathcal{R}^{H}} \sum_{w,n}
    \!\bigl(e^+_{r,w,n} C^R_r + e^-_{r,w,n} U_r C^R_r\bigr)}_{\text{(18) weekly hours}}
+ \;\ldots$$

*(Equation numbers from Knust & Xie 2019. Terms (14), (16), (17), (19) cover
group-coverage, activity-count, working-time, and max-overtime violations.)*

**Arc costs $C^A_a$** encode **per-transition preferences** on the arc connecting
$(s_1, d) \to (s_2, d{+}1)$ for nurse $n$:
- High cost when the combination $(s_1, s_2)$ is undesired (e.g., isolated
  day-off between two work days, shift dissimilarity within a week)
- High cost when $s_2$ is on a day the nurse has requested off (preference term)
- Zero cost for neutral or preferred transitions

**Coverage constraints (flow formulation):**

Hard minimum coverage:
$$\sum_{n \in N_r} y_{s,n} \geq L^{\min}_r \quad \forall\, r \in \mathcal{R}^{C,\text{Hard}},\; s \in S_r$$

Soft coverage (slack variable $c^{\min}_{r,s} \geq 0$ penalised in objective):
$$\sum_{n \in N_r} y_{s,n} \geq L^{\min}_r - c^{\min}_{r,s} \quad \forall\, r \in \mathcal{R}^{C,\text{Soft}},\; s \in S_r$$

**Flow conservation (hard, for all interior nodes):**
$$\sum_{a \in \mathcal{B}_{s,n}} x_a \;=\; \sum_{a \in \mathcal{F}_{s,n}} x_a \;=\; y_{s,n}
\quad \forall\, n,\, d \notin \{d_{\text{first}},\, d_{\text{last}}\},\, s$$

**Single-assignment per day (hard):**
$$\sum_{s \in \mathcal{S}_d} y_{s,n} = 1 \quad \forall\, n \in \mathcal{N},\; d \in \mathcal{D}$$

(Exactly one activity — including DayOff — per nurse per day; one unit of flow.)

---

## INRC-II Soft Constraint Weights (Ceschia et al. 2019, Section 2.5)

These weights enter the objective via penalty slack variables:

| ID | Constraint | Weight |
|---|---|---|
| S1 | Insufficient staffing for optimal coverage | 30 |
| S2 | Consecutive assignments — shift-specific | 15 |
| S2 | Consecutive assignments — global work days | 30 |
| S3 | Consecutive days off | 30 |
| S4 | Nurse shift preferences | 10 |
| S5 | Complete weekend | 30 |
| S6 | Total assignments over planning horizon | 20 |
| S7 | Total working weekends over planning horizon | 30 |

Hard constraints (H1–H4): single assignment, minimum coverage, forbidden
successions, required skill — always enforced as equality/inequality constraints
with no slack.
