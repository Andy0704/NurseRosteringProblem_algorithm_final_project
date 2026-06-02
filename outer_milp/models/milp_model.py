"""MILP formulation layer for the INRC-II Nurse Rostering Problem.

Expects a problem dict conforming to the problem_exchange.json schema:
  - metadata:        { num_nurses, num_days, num_shift_types }
  - shift_mapping:   list of { index, id, name/is }
  - nurse_info:      list of { index, id, contract_id, history }
  - requirements:    { demand_matrix }
  - current_schedule: 2D array [nurse_index][day_index] -> shift_index
"""

import math

import pulp

_REQUIRED_KEYS = frozenset(
    {"metadata", "shift_mapping", "nurse_info", "requirements", "current_schedule"}
)


class MilpModel:

    def __init__(self, data: dict, next_week_data: dict | None = None) -> None:
        missing = _REQUIRED_KEYS - data.keys()
        if missing:
            raise KeyError(
                f"MilpModel: problem data missing required keys: {sorted(missing)}"
            )
        self._data = data
        self._meta = data["metadata"]
        self._nurses = data["nurse_info"]
        self._shifts = data["shift_mapping"]
        self._schedule = data["current_schedule"]
        self._next_week_data = next_week_data
        self._week_days = self._meta["num_days"]          # always 7
        self._full_days = self._week_days * 2 if next_week_data else self._week_days
        self._model = None
        self._x = None

    def build(self) -> None:
        """Build the PuLP LpProblem with H1-H3 hard constraints and S1-S7 soft penalties.

        Assumptions:
          - demand_matrix[d] columns align with work_shifts ordered by shift index
          - Day indices: 0=Mon … 5=Sat, 6=Sun (INRC-II standard)
          - Contract assignment bounds span the full 4-week horizon; prorated to 1 week
          - forbidden_successions keys match shift_mapping[i]["name"] or ["id"]
        Complexity: O(N * D * S) variables, O(N * D * |forbidden_pairs|) for H3.
        """
        N = self._meta["num_nurses"]
        D = self._meta["num_days"]
        S = self._meta["num_shift_types"]

        # Shift index / name helpers
        name_to_idx = {sh.get("name", sh["id"]): sh["index"] for sh in self._shifts}
        idx_to_name = {sh["index"]: sh.get("name", sh["id"]) for sh in self._shifts}
        # work_shifts preserves the order expected by demand_matrix columns
        work_shifts = [sh["index"] for sh in self._shifts if sh.get("is") != "Off"]

        # Forbidden succession pairs (s_from_idx, s_to_idx)
        forbidden_raw = (
            self._data.get("shift_type_constraints", {})
            .get("forbidden_successions", {})
        )
        forbidden_pairs = []
        for from_name, to_names in forbidden_raw.items():
            f = name_to_idx.get(from_name)
            for to_name in to_names:
                t = name_to_idx.get(to_name)
                if f is not None and t is not None:
                    forbidden_pairs.append((f, t))

        demand = self._data["requirements"]["demand_matrix"]
        contracts = self._data.get("contracts", {})

        # INRC-II soft constraint weights (Ceschia et al. 2019)
        W_COVERAGE = 30 # skill-specific coverage deficit
        W_CONSEC = 15   # consecutive shift/working-day violations
        W_OFF = 30      # consecutive days-off violations
        W_ASSIGN = 15   # total assignment count deviation
        W_WEEKEND = 30  # excess working weekends
        W_COMPLETE = 30 # incomplete weekend
        W_PREF = 10     # shift-off request violation

        model = pulp.LpProblem("NRP_INRC2", pulp.LpMinimize)

        # Primary binary decision variables x[n][d][s] ∈ {0,1}
        x = [
            [
                [pulp.LpVariable(f"x_{n}_{d}_{s}", cat="Binary") for s in range(S)]
                for d in range(D)
            ]
            for n in range(N)
        ]

        # ── Hard Constraints ──────────────────────────────────────────────────

        # H1: exactly one shift per nurse per day (including Off at index 0)
        for n in range(N):
            for d in range(D):
                model += (
                    pulp.lpSum(x[n][d][s] for s in range(S)) == 1,
                    f"H1_{n}_{d}",
                )

        # H2: aggregate hard coverage — used only when no per-skill demand data.
        # When demand_by_skill is available, coverage is enforced as a soft
        # constraint (see S_coverage block below) to avoid infeasibility when
        # H3 boundary constraints block the only qualified nurse for a skill/shift.
        skill_demands = self._data.get("requirements", {}).get("demand_by_skill", {})
        if not skill_demands:
            for d in range(D):
                for ws, s in enumerate(work_shifts):
                    model += (
                        pulp.lpSum(x[n][d][s] for n in range(N)) >= demand[d][ws],
                        f"H2_{d}_{s}",
                    )

        # H3: forbidden shift successions within the week
        for n in range(N):
            for d in range(D - 1):
                for s1, s2 in forbidden_pairs:
                    model += (
                        x[n][d][s1] + x[n][d + 1][s2] <= 1,
                        f"H3_{n}_{d}_{s1}_{s2}",
                    )

        # H3 boundary: history last-shift prevents forbidden next shift on day 0
        for n_idx, nurse in enumerate(self._nurses):
            last_s = nurse["history"]["last_shift_index"]
            last_name = idx_to_name.get(last_s, "")
            if last_name in forbidden_raw:
                for to_name in forbidden_raw[last_name]:
                    s_to = name_to_idx.get(to_name)
                    if s_to is not None:
                        model += (x[n_idx][0][s_to] == 0, f"H3h_{n_idx}_{s_to}")

        # ── Soft Constraints ──────────────────────────────────────────────────

        penalty_terms = []  # (weight, LpVariable)
        nurse_id_to_idx = {n["id"]: n["index"] for n in self._nurses}
        SAT, SUN = 5, 6    # Saturday=day5, Sunday=day6 (0=Mon baseline)

        # S_coverage: skill-specific coverage (weight=30, matches penalty_evaluator).
        # Modelled as soft rather than hard to avoid infeasibility when H3 boundary
        # constraints block the only qualified nurse for a required skill/shift slot.
        if skill_demands:
            nurse_has_skill = {
                sk: [sk in nurse["skills"] for nurse in self._nurses]
                for sk in skill_demands
            }
            for sk, sk_demand in skill_demands.items():
                for d in range(D):
                    for ws, s in enumerate(work_shifts):
                        req = sk_demand[d][ws]
                        if req <= 0:
                            continue
                        p = pulp.LpVariable(f"p_H2_{sk}_{d}_{s}", lowBound=0)
                        penalty_terms.append((W_COVERAGE, p))
                        model += (
                            pulp.lpSum(
                                x[n][d][s] for n in range(N) if nurse_has_skill[sk][n]
                            ) + p >= req,
                            f"H2_{sk}_{d}_{s}",
                        )

        for n_idx, nurse in enumerate(self._nurses):
            contract = contracts.get(nurse["contract_id"], {})
            hist = nurse["history"]

            M_w = contract.get("maximumNumberOfConsecutiveWorkingDays", D)
            m_w = contract.get("minimumNumberOfConsecutiveWorkingDays", 1)
            M_o = contract.get("maximumNumberOfConsecutiveDaysOff", D)
            m_o = contract.get("minimumNumberOfConsecutiveDaysOff", 1)
            max_assign = contract.get("maximumNumberOfAssignments", D * 4)
            min_assign = contract.get("minimumNumberOfAssignments", 0)
            max_wknds = contract.get("maximumNumberOfWorkingWeekends", 4)
            complete_wknd = contract.get("completeWeekends", 0)

            h_work = hist["consecutive_working_days"]
            h_off = hist["consecutive_days_off"]
            h_wknd = hist.get("num_working_weekends", 0)

            # Working / off-day indicator expressions (not new variables)
            w = [1 - x[n_idx][d][0] for d in range(D)]    # 1 = working
            off = [x[n_idx][d][0] for d in range(D)]       # 1 = day off

            # S1: Max consecutive working days (window-sum relaxation)
            if h_work > 0:
                remain = M_w - h_work
                if remain < 0:
                    # Already over max; penalise any work on day 0
                    p = pulp.LpVariable(f"p_hw_{n_idx}", lowBound=0)
                    penalty_terms.append((W_CONSEC, p))
                    model += (w[0] <= p, f"S1h_{n_idx}")
                elif remain < D:
                    # History-extended window covers days 0 .. remain
                    p = pulp.LpVariable(f"p_hw_{n_idx}", lowBound=0)
                    penalty_terms.append((W_CONSEC, p))
                    model += (
                        pulp.lpSum(w[:remain + 1]) <= remain + p,
                        f"S1h_{n_idx}",
                    )
                # remain >= D: nurse can work entire week without new violation

            for d in range(D - M_w):
                p = pulp.LpVariable(f"p_mw_{n_idx}_{d}", lowBound=0)
                penalty_terms.append((W_CONSEC, p))
                model += (
                    pulp.lpSum(w[d:d + M_w + 1]) <= M_w + p,
                    f"S1_{n_idx}_{d}",
                )

            # S2: Min consecutive working days (run-start penalty formulation)
            # Constraint w[d] - w_prev - w[d+k] <= pen fires when a run starts at d
            # and the nurse is off at d+k, indicating a run shorter than m_w.
            # For an isolated run of length L: total penalty = m_w - L (matches INRC-II).
            h_was_working = h_work > 0
            for d in range(D):
                w_prev = (1 if h_was_working else 0) if d == 0 else w[d - 1]
                for k in range(1, m_w):
                    if d + k >= D:
                        break
                    p = pulp.LpVariable(f"p_minw_{n_idx}_{d}_{k}", lowBound=0)
                    penalty_terms.append((W_CONSEC, p))
                    model += (w[d] - w_prev - w[d + k] <= p, f"S2_{n_idx}_{d}_{k}")

            # S3: Max consecutive days off (window-sum relaxation, mirrors S1)
            if h_off > 0:
                remain = M_o - h_off
                if remain < 0:
                    p = pulp.LpVariable(f"p_ho_{n_idx}", lowBound=0)
                    penalty_terms.append((W_OFF, p))
                    model += (off[0] <= p, f"S3h_{n_idx}")
                elif remain < D:
                    p = pulp.LpVariable(f"p_ho_{n_idx}", lowBound=0)
                    penalty_terms.append((W_OFF, p))
                    model += (
                        pulp.lpSum(off[:remain + 1]) <= remain + p,
                        f"S3h_{n_idx}",
                    )

            for d in range(D - M_o):
                p = pulp.LpVariable(f"p_mo_{n_idx}_{d}", lowBound=0)
                penalty_terms.append((W_OFF, p))
                model += (
                    pulp.lpSum(off[d:d + M_o + 1]) <= M_o + p,
                    f"S3_{n_idx}_{d}",
                )

            # S4: Min consecutive days off (run-start penalty, mirrors S2)
            h_was_off = h_off > 0
            for d in range(D):
                off_prev = (1 if h_was_off else 0) if d == 0 else off[d - 1]
                for k in range(1, m_o):
                    if d + k >= D:
                        break
                    p = pulp.LpVariable(f"p_mino_{n_idx}_{d}_{k}", lowBound=0)
                    penalty_terms.append((W_OFF, p))
                    model += (
                        off[d] - off_prev - off[d + k] <= p,
                        f"S4_{n_idx}_{d}_{k}",
                    )

            # S5: Total assignment count (prorated weekly from 4-week contract bounds)
            weekly_min = min_assign // 4
            weekly_max = math.ceil(max_assign / 4)
            total_w = pulp.lpSum(w)
            p_u = pulp.LpVariable(f"p_au_{n_idx}", lowBound=0)
            p_o = pulp.LpVariable(f"p_ao_{n_idx}", lowBound=0)
            penalty_terms.append((W_ASSIGN, p_u))
            penalty_terms.append((W_ASSIGN, p_o))
            model += (total_w >= weekly_min - p_u, f"S5_min_{n_idx}")
            model += (total_w <= weekly_max + p_o, f"S5_max_{n_idx}")

            # S7: Working weekends and complete-weekend preference
            if D > SUN:
                wk = pulp.LpVariable(f"wk_{n_idx}", cat="Binary")
                model += (wk >= w[SAT], f"S7a_{n_idx}")
                model += (wk >= w[SUN], f"S7b_{n_idx}")
                p_wk = pulp.LpVariable(f"p_wknd_{n_idx}", lowBound=0)
                penalty_terms.append((W_WEEKEND, p_wk))
                model += (wk + h_wknd - max_wknds <= p_wk, f"S7c_{n_idx}")
                if complete_wknd:
                    p_cpl = pulp.LpVariable(f"p_cpl_{n_idx}", lowBound=0)
                    penalty_terms.append((W_COMPLETE, p_cpl))
                    model += (w[SAT] - w[SUN] <= p_cpl, f"S7d_{n_idx}")
                    model += (w[SUN] - w[SAT] <= p_cpl, f"S7e_{n_idx}")

        # S6: Shift-off requests (nurse preference violations)
        day_name_map = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
            "Friday": 4, "Saturday": 5, "Sunday": 6,
        }
        for req_i, req in enumerate(self._data.get("shift_off_requests", [])):
            n_id = req.get("nurse")
            d = day_name_map.get(req.get("day", ""))
            n_idx = nurse_id_to_idx.get(n_id)
            if n_idx is None or d is None:
                continue
            p = pulp.LpVariable(f"p_pref_{req_i}", lowBound=0)
            penalty_terms.append((W_PREF, p))
            shift_type = req.get("shiftType")
            if shift_type == "Any":
                model += (1 - x[n_idx][d][0] <= p, f"S6_{req_i}")
            else:
                s_req = name_to_idx.get(shift_type)
                if s_req is not None:
                    model += (x[n_idx][d][s_req] <= p, f"S6_{req_i}")

        # Objective: minimise total weighted soft penalty
        model += pulp.lpSum(wt * pv for wt, pv in penalty_terms)

        self._model = model
        self._x = x

    def solve(self, time_limit: int = 30) -> tuple:
        """Solve with CBC and return (schedule_matrix, penalty).

        schedule_matrix: list[list[int]] of shape [num_nurses][num_days],
                         each value is a shift_index (0 = Off).
        penalty:         float, total weighted soft-constraint penalty.

        Raises RuntimeError if called before build() or if CBC finds no incumbent.
        """
        if self._model is None:
            raise RuntimeError("MilpModel.solve() called before build()")

        solver = pulp.getSolver("PULP_CBC_CMD", timeLimit=time_limit, msg=0)
        self._model.solve(solver)

        obj_val = pulp.value(self._model.objective)
        if obj_val is None:
            raise RuntimeError(
                f"MilpModel.solve(): CBC found no feasible solution "
                f"(status={pulp.LpStatus[self._model.status]!r})"
            )

        N = self._meta["num_nurses"]
        D = self._meta["num_days"]
        S = self._meta["num_shift_types"]

        schedule_matrix = [
            [
                next(
                    (s for s in range(S) if (pulp.value(self._x[n][d][s]) or 0) > 0.5),
                    0,  # fallback to Off on floating-point rounding edge cases
                )
                for d in range(D)
            ]
            for n in range(N)
        ]
        penalty = float(obj_val)
        self._schedule = schedule_matrix
        self._data["current_schedule"] = schedule_matrix
        return schedule_matrix, penalty

    def fix_and_optimize(
        self, free_indices: list, current_penalty: float, time_limit: int = 15
    ) -> tuple:
        """Fix all nurses except free_indices, solve sub-model, accept if improved.

        Rebuilds the model from scratch so variable bounds are clean.
        Returns (schedule_matrix, penalty, accepted: bool).
        """
        N = self._meta["num_nurses"]
        original_sched = [row[:] for row in self._schedule]
        fixed = [n for n in range(N) if n not in set(free_indices)]
        self.build()
        self.fix_nurses(fixed)
        try:
            new_sched, new_penalty = self.solve(time_limit=time_limit)
        except RuntimeError:
            self._schedule = original_sched
            self._data["current_schedule"] = original_sched
            return original_sched, current_penalty, False
        if new_penalty < current_penalty:
            return new_sched, new_penalty, True
        self._schedule = original_sched
        self._data["current_schedule"] = original_sched
        return original_sched, current_penalty, False

    def fix_nurses(self, indices: list) -> None:
        """Fix nurses at the given indices to their current_schedule values.

        Constrains x[n][d][s] variables to the values in self._schedule for each
        listed nurse, enabling fix-and-optimise over the remaining free nurses.
        Must be called after build() and before solve().
        """
        if self._model is None:
            raise RuntimeError("MilpModel.fix_nurses() called before build()")
        N = self._meta["num_nurses"]
        D = self._meta["num_days"]
        S = self._meta["num_shift_types"]
        for n in indices:
            if not (0 <= n < N):
                raise IndexError(f"fix_nurses: index {n} out of range [0, {N})")
            for d in range(D):
                s_fixed = self._schedule[n][d]
                for s in range(S):
                    val = 1 if s == s_fixed else 0
                    self._x[n][d][s].lowBound = val
                    self._x[n][d][s].upBound = val
