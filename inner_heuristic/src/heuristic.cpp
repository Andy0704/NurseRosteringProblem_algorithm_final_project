#include "heuristic.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <map>
#include <random>
#include <set>
#include <string>
#include <utility>
#include <vector>

// ============================================================
// Section 1: Penalty weights
// ============================================================
static const int COVER_WEIGHT     = 30;
static const int CONSEC_WEIGHT    = 15;
static const int FORBIDDEN_WEIGHT = 25;
static const int TOTAL_ASSIGN_W   = 10;
static const int SHIFT_OFF_REQ_W  = 10;

// ============================================================
// Section 2: Data structures
// ============================================================
struct Contract {
    int min_assign, max_assign;
    int min_consec_work, max_consec_work;
    int min_consec_off,  max_consec_off;
    int max_working_weekends;
};

struct ShiftDef {
    int  index;
    bool is_off;
    int  min_consecutive;
    int  max_consecutive;
};

struct NurseData {
    int                      index;
    std::string              contract_id;
    std::vector<std::string> skills;
    int hist_consec_work;
    int hist_consec_off;
    int hist_last_shift;
    int hist_num_assign;
    int hist_consec_same_shift;
};

struct ShiftOffReq {
    int nurse_idx;
    int day;        // 0-6 (Monday = 0)
    int shift_idx;  // -1 = Any
};

struct Problem {
    int num_nurses;
    int num_days;
    int num_shifts;

    std::vector<NurseData>              nurses;
    std::map<std::string, Contract>     contracts;
    std::vector<ShiftDef>               shifts;

    // demand_by_skill[skill_name][day][shift_col]  (shift_col = shift_index - 1)
    std::map<std::string, std::vector<std::vector<int>>> demand_by_skill;

    // (from_shift_idx, to_shift_idx) pairs that are forbidden
    std::set<std::pair<int,int>> forbidden_succ;

    std::vector<ShiftOffReq>           off_requests;
    std::vector<std::vector<int>>      schedule; // schedule[nurse][day]

    std::map<std::string, int> shift_id_to_idx; // "Early"->1, "Late"->2, "Night"->3
};

// ============================================================
// Section 3: parseProblem -- JSON -> Problem
// ============================================================
static Problem parseProblem(const nlohmann::json& data) {
    Problem prob;

    const auto& meta = data.at("metadata");
    prob.num_nurses  = meta.at("num_nurses").get<int>();
    prob.num_days    = meta.at("num_days").get<int>();
    prob.num_shifts  = meta.at("num_shift_types").get<int>();

    // shift_mapping
    prob.shifts.resize(prob.num_shifts);
    for (const auto& sm : data.at("shift_mapping")) {
        ShiftDef sd;
        sd.index           = sm.at("index").get<int>();
        sd.is_off          = (sm.contains("is") && sm.at("is") == "Off");
        sd.min_consecutive = sm.value("min_consecutive", 1);
        sd.max_consecutive = sm.value("max_consecutive", 30);
        prob.shifts[sd.index] = sd;
        prob.shift_id_to_idx[sm.at("id").get<std::string>()] = sd.index;
    }

    // contracts
    for (const auto& [cid, cv] : data.at("contracts").items()) {
        Contract c;
        c.min_assign       = cv.value("minimumNumberOfAssignments", 0);
        c.max_assign       = cv.value("maximumNumberOfAssignments", 999);
        c.min_consec_work  = cv.value("minimumNumberOfConsecutiveWorkingDays", 1);
        c.max_consec_work  = cv.value("maximumNumberOfConsecutiveWorkingDays", 30);
        c.min_consec_off   = cv.value("minimumNumberOfConsecutiveDaysOff", 1);
        c.max_consec_off   = cv.value("maximumNumberOfConsecutiveDaysOff", 30);
        c.max_working_weekends = cv.value("maximumNumberOfWorkingWeekends", 999);
        prob.contracts[cid] = c;
    }

    // nurse_info
    prob.nurses.resize(prob.num_nurses);
    for (const auto& ni : data.at("nurse_info")) {
        NurseData n;
        n.index       = ni.at("index").get<int>();
        n.contract_id = ni.at("contract_id").get<std::string>();
        for (const auto& s : ni.at("skills"))
            n.skills.push_back(s.get<std::string>());
        const auto& h            = ni.at("history");
        n.hist_consec_work       = h.value("consecutive_working_days",            0);
        n.hist_consec_off        = h.value("consecutive_days_off",                 0);
        n.hist_last_shift        = h.value("last_shift_index",                    0);
        n.hist_num_assign        = h.value("num_assignments",                     0);
        n.hist_consec_same_shift = h.value("num_consecutive_shift_assignments",   0);
        prob.nurses[n.index] = n;
    }

    // demand_by_skill
    const auto& reqs = data.at("requirements");
    for (const auto& [sk, sk_data] : reqs.at("demand_by_skill").items())
        prob.demand_by_skill[sk] = sk_data.get<std::vector<std::vector<int>>>();

    // forbidden_successions: {from_shift_name: [to_shift_name, ...]}
    const auto& fc = data.at("shift_type_constraints").at("forbidden_successions");
    for (const auto& [from_name, to_list] : fc.items()) {
        auto it = prob.shift_id_to_idx.find(from_name);
        if (it == prob.shift_id_to_idx.end()) continue;
        int from_idx = it->second;
        for (const auto& to_name : to_list) {
            auto it2 = prob.shift_id_to_idx.find(to_name.get<std::string>());
            if (it2 != prob.shift_id_to_idx.end())
                prob.forbidden_succ.insert({from_idx, it2->second});
        }
    }

    // shift_off_requests
    static const std::map<std::string, int> DAY_IDX = {
        {"Monday",0}, {"Tuesday",1}, {"Wednesday",2}, {"Thursday",3},
        {"Friday",4}, {"Saturday",5}, {"Sunday",6}
    };
    std::map<std::string, int> nurse_name_idx;
    for (const auto& ni : data.at("nurse_info"))
        nurse_name_idx[ni.at("id").get<std::string>()] = ni.at("index").get<int>();

    for (const auto& req : data.at("shift_off_requests")) {
        auto it_n = nurse_name_idx.find(req.at("nurse").get<std::string>());
        auto it_d = DAY_IDX.find(req.at("day").get<std::string>());
        if (it_n == nurse_name_idx.end() || it_d == DAY_IDX.end()) continue;
        ShiftOffReq sor;
        sor.nurse_idx = it_n->second;
        sor.day       = it_d->second;
        const std::string st = req.at("shiftType").get<std::string>();
        if (st == "Any") {
            sor.shift_idx = -1;
        } else {
            auto it_s = prob.shift_id_to_idx.find(st);
            if (it_s == prob.shift_id_to_idx.end()) continue;
            sor.shift_idx = it_s->second;
        }
        prob.off_requests.push_back(sor);
    }

    // current_schedule
    prob.schedule = data.at("current_schedule").get<std::vector<std::vector<int>>>();

    return prob;
}

// ============================================================
// Section 4a: Coverage cost for a single day
// ============================================================
static int coverageCostDay(const Problem& prob,
                           const std::vector<std::vector<int>>& sched,
                           int d)
{
    std::map<std::string, std::vector<int>> skill_count;
    for (const auto& [sk, _] : prob.demand_by_skill)
        skill_count[sk].assign(prob.num_shifts, 0);

    for (int n = 0; n < prob.num_nurses; n++) {
        int s = sched[n][d];
        if (s == 0) continue;
        for (const auto& sk : prob.nurses[n].skills)
            if (skill_count.count(sk)) skill_count[sk][s]++;
    }

    int penalty = 0;
    for (const auto& [sk, demands] : prob.demand_by_skill) {
        const auto& cnt = skill_count.at(sk);
        for (int s = 1; s < prob.num_shifts; s++) {
            int deficit = demands[d][s - 1] - cnt[s];
            if (deficit > 0) penalty += deficit * COVER_WEIGHT;
        }
    }
    return penalty;
}

// ============================================================
// Section 4a-bis: H2 deficit units for a single day (SA-only)
// Same loop as coverageCostDay, but returns the raw count of
// nurse-units below minimum (no COVER_WEIGHT). Used only by the
// SA acceptance/best-update path -- never by runEvalOnly.
// ============================================================
static int coverageDeficitUnitsDay(const Problem& prob,
                                   const std::vector<std::vector<int>>& sched,
                                   int d)
{
    std::map<std::string, std::vector<int>> skill_count;
    for (const auto& [sk, _] : prob.demand_by_skill)
        skill_count[sk].assign(prob.num_shifts, 0);

    for (int n = 0; n < prob.num_nurses; n++) {
        int s = sched[n][d];
        if (s == 0) continue;
        for (const auto& sk : prob.nurses[n].skills)
            if (skill_count.count(sk)) skill_count[sk][s]++;
    }

    int units = 0;
    for (const auto& [sk, demands] : prob.demand_by_skill) {
        const auto& cnt = skill_count.at(sk);
        for (int s = 1; s < prob.num_shifts; s++) {
            int deficit = demands[d][s - 1] - cnt[s];
            if (deficit > 0) units += deficit;
        }
    }
    return units;
}

// ============================================================
// Section 4a-ter: total H2 deficit units across all days (SA-only)
// ============================================================
static int totalH2Units(const Problem& prob,
                        const std::vector<std::vector<int>>& sched)
{
    int units = 0;
    for (int d = 0; d < prob.num_days; d++)
        units += coverageDeficitUnitsDay(prob, sched, d);
    return units;
}

// ============================================================
// Section 4a-quater: H3 forbidden-succession violations on the
// transition INTO day d, summed across all nurses (SA-only).
// For d==0 this is the cross-week boundary transition
// (history.last_shift_index -> sched[n][0]); for d>=1 it is the
// within-week transition (sched[n][d-1] -> sched[n][d]). Mirrors
// coverageDeficitUnitsDay's per-day, all-nurses pattern.
// ============================================================
static int forbiddenViolationsDay(const Problem& prob,
                                   const std::vector<std::vector<int>>& sched,
                                   int d)
{
    int count = 0;
    for (int n = 0; n < prob.num_nurses; n++) {
        int from, to;
        if (d == 0) {
            from = prob.nurses[n].hist_last_shift;
            to   = sched[n][0];
        } else {
            from = sched[n][d - 1];
            to   = sched[n][d];
        }
        if (from != 0 && to != 0 && prob.forbidden_succ.count({from, to}))
            count++;
    }
    return count;
}

// ============================================================
// Section 4a-quinquies: total H3 forbidden-succession violations
// across all days (SA-only). Equal to the sum of
// nurseCostFull(...).forbidden_hard over all nurses (D transitions
// per nurse: 1 boundary + (D-1) within-week).
// ============================================================
static int totalForbiddenViolations(const Problem& prob,
                                     const std::vector<std::vector<int>>& sched)
{
    int total = 0;
    for (int d = 0; d < prob.num_days; d++)
        total += forbiddenViolationsDay(prob, sched, d);
    return total;
}

// ============================================================
// Section 4b: Per-nurse cost breakdown struct + full cost function
// ============================================================

// NurseCost: per-component breakdown returned by nurseCostFull.
// forbidden_hard is an H3 hard-constraint count — NOT included in total.
// total = s2_consec_work + s3_consec_off + s4_pref + assignment (soft only).
struct NurseCost {
    int s2_consec_work = 0;
    int s3_consec_off  = 0;
    int s4_pref        = 0;
    int forbidden_hard = 0;
    int total          = 0;
};

static NurseCost nurseCostFull(const Problem& prob,
                               const std::vector<std::vector<int>>& sched,
                               int n)
{
    const NurseData& nurse    = prob.nurses[n];
    const Contract&  contract = prob.contracts.at(nurse.contract_id);
    const int D = prob.num_days;
    NurseCost nc;

    // Forbidden successions — H3 HARD constraint (Change D):
    // count violations separately; do NOT add to soft total.
    if (nurse.hist_last_shift != 0 && sched[n][0] != 0) {
        if (prob.forbidden_succ.count({nurse.hist_last_shift, sched[n][0]}))
            nc.forbidden_hard++;
    }
    for (int d = 1; d < D; d++) {
        int from = sched[n][d - 1], to = sched[n][d];
        if (from != 0 && to != 0 && prob.forbidden_succ.count({from, to}))
            nc.forbidden_hard++;
    }

    // Consecutive working days — transition-based (Change A):
    // Scores proportionally at work→off transitions; defers open runs (matches evaluator).
    {
        int run = 0;
        for (int d = 0; d < D; d++) {
            if (sched[n][d] != 0) {
                run++;
                if (d == 0 && nurse.hist_consec_work > 0)
                    run += nurse.hist_consec_work;
            } else {
                if (run > 0) {
                    int pen = 0;
                    if (run < contract.min_consec_work)
                        pen = (contract.min_consec_work - run) * CONSEC_WEIGHT;
                    else if (run > contract.max_consec_work)
                        pen = (run - contract.max_consec_work) * CONSEC_WEIGHT;
                    nc.s2_consec_work += pen;
                    nc.total          += pen;
                    run = 0;
                }
            }
        }
        // No post-loop check: open run at week end is deferred to next week (matches evaluator).
    }

    // Consecutive days off — transition-based (Change B):
    // Scores proportionally at off→work transitions; defers open runs (matches evaluator).
    {
        int run = 0;
        for (int d = 0; d < D; d++) {
            if (sched[n][d] == 0) {
                run++;
                if (d == 0 && nurse.hist_consec_work == 0)
                    run += nurse.hist_consec_off;
            } else {
                if (run > 0) {
                    int pen = 0;
                    if (run < contract.min_consec_off)
                        pen = (contract.min_consec_off - run) * CONSEC_WEIGHT;
                    else if (run > contract.max_consec_off)
                        pen = (run - contract.max_consec_off) * CONSEC_WEIGHT;
                    nc.s3_consec_off += pen;
                    nc.total         += pen;
                    run = 0;
                }
            }
        }
        // No post-loop check: open run at week end is deferred to next week (matches evaluator).
    }

    // Total assignments — weekly prorated bounds (aligned with MILP S5).
    {
        int worked = 0;
        for (int d = 0; d < D; d++) if (sched[n][d] != 0) worked++;
        const int weekly_min = contract.min_assign / 4;
        const int weekly_max = (contract.max_assign + 3) / 4;
        int pen = 0;
        if (worked < weekly_min) pen = TOTAL_ASSIGN_W * (weekly_min - worked);
        else if (worked > weekly_max) pen = TOTAL_ASSIGN_W * (worked - weekly_max);
        nc.total += pen;
    }

    // Consecutive same-shift type — Change C: removed (no equivalent in evaluator or MILP).

    // Shift-off requests (S4).
    for (const auto& sor : prob.off_requests) {
        if (sor.nurse_idx != n || sor.day >= D) continue;
        int assigned = sched[n][sor.day];
        int pen = 0;
        if (sor.shift_idx == -1 && assigned != 0)
            pen = SHIFT_OFF_REQ_W;
        else if (sor.shift_idx > 0 && assigned == sor.shift_idx)
            pen = SHIFT_OFF_REQ_W;
        nc.s4_pref += pen;
        nc.total   += pen;
    }

    return nc;
}

// ============================================================
// Section 4c: Full schedule cost
// ============================================================
static int fullCost(const Problem& prob,
                    const std::vector<std::vector<int>>& sched)
{
    int cost = 0;
    for (int d = 0; d < prob.num_days; d++)
        cost += coverageCostDay(prob, sched, d);
    for (int n = 0; n < prob.num_nurses; n++)
        cost += nurseCostFull(prob, sched, n).total;
    return cost;
}

// ============================================================
// Section 4d: Delta evaluation -- TwoWaySwap(n1, n2, day d)
// Complexity: O(N + D) -- only recomputes day-d coverage and
// the two affected nurses' full schedules.
// ============================================================
static int deltaTwoWaySwap(const Problem& prob,
                           std::vector<std::vector<int>>& sched,
                           int n1, int n2, int d, int M_COVER, int M_FORBID)
{
    int old_units   = coverageDeficitUnitsDay(prob, sched, d);
    int old_partial = coverageCostDay(prob, sched, d)
                    + nurseCostFull(prob, sched, n1).total
                    + nurseCostFull(prob, sched, n2).total;
    int old_h3 = forbiddenViolationsDay(prob, sched, d)
               + (d + 1 < prob.num_days ? forbiddenViolationsDay(prob, sched, d + 1) : 0);

    std::swap(sched[n1][d], sched[n2][d]);

    int new_units   = coverageDeficitUnitsDay(prob, sched, d);
    int new_partial = coverageCostDay(prob, sched, d)
                    + nurseCostFull(prob, sched, n1).total
                    + nurseCostFull(prob, sched, n2).total;
    int new_h3 = forbiddenViolationsDay(prob, sched, d)
               + (d + 1 < prob.num_days ? forbiddenViolationsDay(prob, sched, d + 1) : 0);

    std::swap(sched[n1][d], sched[n2][d]); // revert -- caller decides whether to keep

    return (new_partial - old_partial) + M_COVER * (new_units - old_units)
         + M_FORBID * (new_h3 - old_h3);
}

// ============================================================
// Section 5: Delta evaluation -- RandomDayOff(nurse n, working day d)
// Sets sched[n][d] = 0 (day off); reverts after delta measurement.
// Complexity: O(N + D)
// ============================================================
static int deltaRandomDayOff(const Problem& prob,
                              std::vector<std::vector<int>>& sched,
                              int n, int d, int M_COVER, int M_FORBID)
{
    int old_units   = coverageDeficitUnitsDay(prob, sched, d);
    int old_partial = coverageCostDay(prob, sched, d)
                    + nurseCostFull(prob, sched, n).total;
    int old_h3 = forbiddenViolationsDay(prob, sched, d)
               + (d + 1 < prob.num_days ? forbiddenViolationsDay(prob, sched, d + 1) : 0);

    const int old_shift = sched[n][d];
    sched[n][d] = 0;

    int new_units   = coverageDeficitUnitsDay(prob, sched, d);
    int new_partial = coverageCostDay(prob, sched, d)
                    + nurseCostFull(prob, sched, n).total;
    int new_h3 = forbiddenViolationsDay(prob, sched, d)
               + (d + 1 < prob.num_days ? forbiddenViolationsDay(prob, sched, d + 1) : 0);

    sched[n][d] = old_shift; // revert

    return (new_partial - old_partial) + M_COVER * (new_units - old_units)
         + M_FORBID * (new_h3 - old_h3);
}

// ============================================================
// Section 5b: Delta evaluation -- ShiftTypeChange(nurse n, day d, new shift s')
// Sets sched[n][d] = s_new (any shift != current, including 0=off and
// off->work); reverts after delta measurement. Mirrors deltaRandomDayOff.
// Complexity: O(N + D)
// ============================================================
static int deltaShiftTypeChange(const Problem& prob,
                                 std::vector<std::vector<int>>& sched,
                                 int n, int d, int s_new, int M_COVER, int M_FORBID)
{
    int old_units   = coverageDeficitUnitsDay(prob, sched, d);
    int old_partial = coverageCostDay(prob, sched, d)
                    + nurseCostFull(prob, sched, n).total;
    int old_h3 = forbiddenViolationsDay(prob, sched, d)
               + (d + 1 < prob.num_days ? forbiddenViolationsDay(prob, sched, d + 1) : 0);

    const int old_shift = sched[n][d];
    sched[n][d] = s_new;

    int new_units   = coverageDeficitUnitsDay(prob, sched, d);
    int new_partial = coverageCostDay(prob, sched, d)
                    + nurseCostFull(prob, sched, n).total;
    int new_h3 = forbiddenViolationsDay(prob, sched, d)
               + (d + 1 < prob.num_days ? forbiddenViolationsDay(prob, sched, d + 1) : 0);

    sched[n][d] = old_shift; // revert

    return (new_partial - old_partial) + M_COVER * (new_units - old_units)
         + M_FORBID * (new_h3 - old_h3);
}

// ============================================================
// Section 6: T0 estimation
// Upper-bounds max single-nurse cost by testing exhaustive
// fill schedules (all-X and alternating Night/Early).
// T0 = 20 * max_single_nurse_cost  (Knust 2019, multiplier = 20)
// ============================================================
static double computeT0(const Problem& prob,
                        const std::vector<std::vector<int>>& sched)
{
    int max_nurse_cost = 1;
    std::vector<std::vector<int>> tmp = sched;

    for (int n = 0; n < prob.num_nurses; n++) {
        // All-same-shift scenarios
        for (int fill = 1; fill < prob.num_shifts; fill++) {
            for (int d = 0; d < prob.num_days; d++) tmp[n][d] = fill;
            int c = nurseCostFull(prob, tmp, n).total;
            if (c > max_nurse_cost) max_nurse_cost = c;
        }
        // Alternating Night(3)/Early(1): maximises forbidden successions
        for (int d = 0; d < prob.num_days; d++)
            tmp[n][d] = (d % 2 == 0) ? 3 : 1;
        int c = nurseCostFull(prob, tmp, n).total;
        if (c > max_nurse_cost) max_nurse_cost = c;
        // Restore row
        for (int d = 0; d < prob.num_days; d++) tmp[n][d] = sched[n][d];
    }

    double T0 = 20.0 * max_nurse_cost;
    return (T0 < 10.0) ? 10.0 : T0;
}

// ============================================================
// Sections 7-10: SA main loop with Late Acceptance
//
// Parameters (CLAUDE.md):
//   SA: T0=20*max_cost, beta=0.9, COOL_EVERY=30000, T_MIN=10,
//       NO_IMPROVE_MAX=500000
//   Late Acceptance: gamma=150, accept if Z(s') < L[iter mod 150]
//
// Operators:
//   70% TwoWaySwap      -- swap two nurses' shifts on one day
//   15% RandomDayOff    -- assign day off to one nurse on one working day
//   15% ShiftTypeChange -- change one nurse-day to a different shift
//                          (only operator with off->work mobility; Knust 2019)
// ============================================================
nlohmann::json runHeuristic(const nlohmann::json& data) {
    Problem prob          = parseProblem(data);
    auto    sched         = prob.schedule;
    const int initial_cost = fullCost(prob, sched);

    // Fail loud (Rule 12): the MILP-seeded incoming schedule must already be
    // H2-feasible (minimum coverage). SA may traverse temporary H2 violations,
    // but it should never have to fix an infeasible starting point.
    const int initial_units = totalH2Units(prob, sched);
    if (initial_units > 0) {
        std::cerr << "[nrp_heuristic] WARNING: incoming schedule violates H2 "
                     "minimum coverage (totalH2Units=" << initial_units
                  << "). MILP seed should be H2-feasible.\n";
    }

    // Fail loud (Rule 12): the MILP+F&O-seeded incoming schedule must already
    // be H3-feasible (no forbidden successions). SA may traverse temporary
    // H3 violations, but it should never have to fix an infeasible starting
    // point.
    const int initial_h3 = totalForbiddenViolations(prob, sched);
    if (initial_h3 > 0) {
        std::cerr << "[nrp_heuristic] WARNING: incoming schedule has "
                  << initial_h3
                  << " H3 forbidden-succession violations. MILP+F&O seed "
                     "should be H3-feasible.\n";
    }

    auto best_sched = sched;

    // SA / LA parameters
    const double BETA          = 0.9;
    const int    COOL_EVERY    = 30000;
    const double T_MIN         = 10.0;
    const int    NO_IMPROVE_MAX = 500000;
    const int    GAMMA         = 150;

    double T = computeT0(prob, sched);

    // ============================================================
    // M_COVER: big-M penalty for temporary H2 (minimum coverage)
    // violations during SA search, derived from T0 (Knust 2019).
    // M_COVER = ceil(-ln(p0) * T0), p0 = 0.05 (5% acceptance
    // probability for a unit H2 violation at peak temperature T0)
    // ~= 3.0 * T0. Proportional to deficit units (M_COVER * units),
    // never flat. This penalty exists ONLY in the SA acceptance
    // path (cur_cost) and the best_sched gate below -- it never
    // enters coverageCostDay, nurseCostFull, fullCost, or the
    // reported final_cost.
    // ============================================================
    const int M_COVER = static_cast<int>(std::ceil(-std::log(0.05) * T));

    // ============================================================
    // M_FORBID: big-M penalty for temporary H3 (forbidden-succession)
    // violations during SA search, mirroring M_COVER's derivation
    // (Knust 2019, p0 = 0.05 -> M = ceil(-ln(p0) * T0) ~= 3.0 * T0).
    // H3 is an INRC-II hard constraint (Ceschia 2019 sec 2.5.1). Like
    // H2, big-M soft allows high-T exploration of H3-creating moves
    // (6.5% of all accepts are H3-creating net-improving moves on
    // n012w8 W3, per the 2026-06-15 trajectory diagnostic) while the
    // best_sched gate below ensures the returned solution is always
    // H3-clean. This penalty exists ONLY in the SA acceptance path
    // (cur_cost) and the best_sched gate -- it never enters
    // coverageCostDay, nurseCostFull, fullCost, or the reported
    // final_cost.
    // ============================================================
    const int M_FORBID = static_cast<int>(std::ceil(-std::log(0.05) * T));

    // Invariant: cur_cost_k = fullCost(s_k) + M_COVER * totalH2Units(s_k)
    //                       + M_FORBID * totalForbiddenViolations(s_k) for all k.
    // best_cost is only updated when totalH2Units(s_k)==0 AND
    // totalForbiddenViolations(s_k)==0, so best_cost is always a clean
    // fullCost value. final_cost = best_cost is therefore M_COVER-/M_FORBID-free.
    int cur_cost  = initial_cost + M_COVER * initial_units + M_FORBID * initial_h3;
    int best_cost = cur_cost;

    // Late Acceptance circular buffer
    std::vector<int> la_list(GAMMA, cur_cost);

    std::mt19937 rng(42);
    std::uniform_real_distribution<double> uni01(0.0, 1.0);
    std::uniform_int_distribution<int>     nurse_dist(0, prob.num_nurses - 1);
    std::uniform_int_distribution<int>     day_dist(0, prob.num_days - 1);
    std::uniform_int_distribution<int>     shift_offset_dist(1, prob.num_shifts - 1);

    long long iter        = 0;
    int       no_improve  = 0;

    while (T > T_MIN && no_improve < NO_IMPROVE_MAX) {

        int delta = 0;
        bool move_valid = false;
        int op_n1 = -1, op_n2 = -1, op_d = -1; // TwoWaySwap params
        int doff_n = -1, doff_d = -1;            // RandomDayOff params
        int stc_n = -1, stc_d = -1, stc_s = -1;  // ShiftTypeChange params
        const double op_pick = uni01(rng);

        if (op_pick >= 0.85) {
            // ShiftTypeChange (15%): pick nurse/day, change to a different
            // shift (uniform over the num_shifts-1 alternatives, including
            // 0=off). Only operator with off->work mobility.
            int n = nurse_dist(rng);
            int d = day_dist(rng);
            int s_new = (sched[n][d] + shift_offset_dist(rng)) % prob.num_shifts;
            delta  = deltaShiftTypeChange(prob, sched, n, d, s_new, M_COVER, M_FORBID);
            stc_n  = n; stc_d = d; stc_s = s_new;
            move_valid = true;
        } else if (op_pick >= 0.70) {
            // RandomDayOff (15%): pick nurse, collect working days, pick one
            int n = nurse_dist(rng);
            std::vector<int> working;
            for (int d = 0; d < prob.num_days; d++)
                if (sched[n][d] != 0) working.push_back(d);
            if (!working.empty()) {
                std::uniform_int_distribution<int> wd(0, (int)working.size() - 1);
                int d = working[wd(rng)];
                delta      = deltaRandomDayOff(prob, sched, n, d, M_COVER, M_FORBID);
                doff_n     = n;
                doff_d     = d;
                move_valid = true;
            }
        }

        if (!move_valid) {
            // TwoWaySwap (70%, also fallback when no working day found for DayOff)
            int n1 = nurse_dist(rng);
            int n2 = nurse_dist(rng);
            while (n2 == n1 && prob.num_nurses > 1) n2 = nurse_dist(rng);
            int d  = day_dist(rng);
            delta  = deltaTwoWaySwap(prob, sched, n1, n2, d, M_COVER, M_FORBID);
            op_n1  = n1; op_n2 = n2; op_d = d;
            move_valid = true;
        }

        // Acceptance: improvement OR Late Acceptance OR Metropolis
        const int  la_ref  = la_list[iter % GAMMA];
        const bool accept  = (delta < 0)
                          || ((cur_cost + delta) < la_ref)
                          || (uni01(rng) < std::exp(-static_cast<double>(delta) / T));

        if (accept) {
            if (stc_n >= 0) {
                sched[stc_n][stc_d] = stc_s;
            } else if (doff_n >= 0) {
                sched[doff_n][doff_d] = 0;
            } else {
                std::swap(sched[op_n1][op_d], sched[op_n2][op_d]);
            }
            cur_cost += delta;

            // best_sched gate: cur_cost includes the M_COVER/M_FORBID surcharges,
            // but the surcharges alone are not guaranteed to dominate on
            // large-N instances. Require explicit H2- and H3-feasibility
            // (totalH2Units==0 && totalForbiddenViolations==0) before
            // promoting a state to best_sched, so the returned solution is
            // always H2- and H3-clean.
            if (cur_cost < best_cost
                && totalH2Units(prob, sched) == 0
                && totalForbiddenViolations(prob, sched) == 0) {
                best_cost  = cur_cost;
                best_sched = sched;
                no_improve = 0;
            } else {
                no_improve++;
            }
        } else {
            no_improve++;
        }

        // Update LA list (always, regardless of acceptance)
        la_list[iter % GAMMA] = cur_cost;

        iter++;
        if (iter % COOL_EVERY == 0) T *= BETA;
    }

    // Diagnostic-only (stderr, not part of the data contract): termination state.
    // Only runHeuristic reaches this line; --eval-only calls runEvalOnly directly
    // and never prints this, so the identity tests stay silent on stdout/stderr.
    std::cerr << "[nrp_heuristic] DIAG iter=" << iter
              << " no_improve=" << no_improve
              << " T=" << T
              << " T0=" << computeT0(prob, prob.schedule)
              << " M_COVER=" << M_COVER
              << " terminated_by=" << (no_improve >= NO_IMPROVE_MAX ? "NO_IMPROVE_MAX" : "T_MIN")
              << "\n";

    // best_cost = fullCost(best_sched) + M_COVER * totalH2Units(best_sched)
    //           + M_FORBID * totalForbiddenViolations(best_sched)
    // (invariant above). Strip both surcharge terms so final_cost is always
    // a clean fullCost value, even if best_sched never reached H2-/H3-
    // feasibility (i.e. best_sched == seed and totalH2Units(seed) > 0 or
    // totalForbiddenViolations(seed) > 0).
    const int final_cost = best_cost
                          - M_COVER  * totalH2Units(prob, best_sched)
                          - M_FORBID * totalForbiddenViolations(prob, best_sched);

    nlohmann::json result = data;
    result["current_schedule"]          = best_sched;
    result["metadata"]["initial_cost"]  = initial_cost;
    result["metadata"]["final_cost"]    = final_cost;
    return result;
}

// ===========================================================
// runEvalOnly: evaluate the current_schedule in data and return
// a per-component JSON breakdown (thin wrapper, no new logic).
// total = S1 + S2 + S3 + S4 (matches evaluator structure; hard
// constraints excluded — forbidden returned as separate count).
// ============================================================
nlohmann::json runEvalOnly(const nlohmann::json& data)
{
    Problem prob = parseProblem(data);
    const auto& sched = prob.schedule;

    int s1 = 0, s2 = 0, s3 = 0, s4 = 0, forbidden_hard = 0;
    for (int d = 0; d < prob.num_days; d++)
        s1 += coverageCostDay(prob, sched, d);
    for (int n = 0; n < prob.num_nurses; n++) {
        NurseCost nc = nurseCostFull(prob, sched, n);
        s2            += nc.s2_consec_work;
        s3            += nc.s3_consec_off;
        s4            += nc.s4_pref;
        forbidden_hard += nc.forbidden_hard;
    }
    int total = s1 + s2 + s3 + s4;

    nlohmann::json out;
    out["S1_coverage"]                = s1;
    out["S2_consecutive_work"]        = s2;
    out["S3_consecutive_off"]         = s3;
    out["S4_preferences"]             = s4;
    out["forbidden_violations"]       = forbidden_hard;
    out["total"]                      = total;
    return out;
}
