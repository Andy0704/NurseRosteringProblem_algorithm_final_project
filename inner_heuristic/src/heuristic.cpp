#include "heuristic.h"

#include <algorithm>
#include <cmath>
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
static const int SHIFT_OFF_REQ_W  = 5;

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
// Section 4b: Full soft-constraint cost for a single nurse
// ============================================================
static int nurseCostFull(const Problem& prob,
                         const std::vector<std::vector<int>>& sched,
                         int n)
{
    const NurseData& nurse    = prob.nurses[n];
    const Contract&  contract = prob.contracts.at(nurse.contract_id);
    const int D = prob.num_days;
    int penalty = 0;

    // Forbidden successions (including cross-week boundary)
    if (nurse.hist_last_shift != 0 && sched[n][0] != 0) {
        if (prob.forbidden_succ.count({nurse.hist_last_shift, sched[n][0]}))
            penalty += FORBIDDEN_WEIGHT;
    }
    for (int d = 1; d < D; d++) {
        int from = sched[n][d - 1], to = sched[n][d];
        if (from != 0 && to != 0 && prob.forbidden_succ.count({from, to}))
            penalty += FORBIDDEN_WEIGHT;
    }

    // Consecutive working days (initialised from history)
    {
        int run = nurse.hist_consec_work;
        for (int d = 0; d < D; d++) {
            if (sched[n][d] != 0) {
                run++;
                if (run > contract.max_consec_work) penalty += CONSEC_WEIGHT;
            } else {
                if (run > 0 && run < contract.min_consec_work) penalty += CONSEC_WEIGHT;
                run = 0;
            }
        }
        if (run > contract.max_consec_work) penalty += CONSEC_WEIGHT;
    }

    // Consecutive days off (initialised from history)
    {
        int run = (nurse.hist_consec_work > 0) ? 0 : nurse.hist_consec_off;
        for (int d = 0; d < D; d++) {
            if (sched[n][d] == 0) {
                run++;
                if (run > contract.max_consec_off) penalty += CONSEC_WEIGHT;
            } else {
                if (run > 0 && run < contract.min_consec_off) penalty += CONSEC_WEIGHT;
                run = 0;
            }
        }
        if (run > contract.max_consec_off) penalty += CONSEC_WEIGHT;
    }

    // Total assignments
    {
        int total = nurse.hist_num_assign;
        for (int d = 0; d < D; d++) if (sched[n][d] != 0) total++;
        if (total < contract.min_assign) penalty += TOTAL_ASSIGN_W * (contract.min_assign - total);
        if (total > contract.max_assign) penalty += TOTAL_ASSIGN_W * (total - contract.max_assign);
    }

    // Consecutive same-shift type (current week only)
    {
        int cur_shift = 0, run = 0;
        for (int d = 0; d < D; d++) {
            int s = sched[n][d];
            if (s != 0 && s == cur_shift) {
                run++;
                if (run > prob.shifts[cur_shift].max_consecutive) penalty += CONSEC_WEIGHT;
            } else {
                if (cur_shift != 0 && run > 0 && run < prob.shifts[cur_shift].min_consecutive)
                    penalty += CONSEC_WEIGHT;
                cur_shift = s;
                run = (s != 0) ? 1 : 0;
            }
        }
        if (cur_shift != 0 && run > prob.shifts[cur_shift].max_consecutive)
            penalty += CONSEC_WEIGHT;
    }

    // Shift-off requests
    for (const auto& sor : prob.off_requests) {
        if (sor.nurse_idx != n || sor.day >= D) continue;
        int assigned = sched[n][sor.day];
        if (sor.shift_idx == -1 && assigned != 0)
            penalty += SHIFT_OFF_REQ_W;
        else if (sor.shift_idx > 0 && assigned == sor.shift_idx)
            penalty += SHIFT_OFF_REQ_W;
    }

    return penalty;
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
        cost += nurseCostFull(prob, sched, n);
    return cost;
}

// ============================================================
// Section 4d: Delta evaluation -- TwoWaySwap(n1, n2, day d)
// Complexity: O(N + D) -- only recomputes day-d coverage and
// the two affected nurses' full schedules.
// ============================================================
static int deltaTwoWaySwap(const Problem& prob,
                           std::vector<std::vector<int>>& sched,
                           int n1, int n2, int d)
{
    int old_partial = coverageCostDay(prob, sched, d)
                    + nurseCostFull(prob, sched, n1)
                    + nurseCostFull(prob, sched, n2);

    std::swap(sched[n1][d], sched[n2][d]);

    // Hard coverage check: reject if swap creates any demand deficit on day d
    int new_cov = coverageCostDay(prob, sched, d);
    if (new_cov > 0) {
        std::swap(sched[n1][d], sched[n2][d]); // revert
        return 999999;
    }

    int new_partial = new_cov
                    + nurseCostFull(prob, sched, n1)
                    + nurseCostFull(prob, sched, n2);

    std::swap(sched[n1][d], sched[n2][d]); // revert -- caller decides whether to keep

    return new_partial - old_partial;
}

// ============================================================
// Section 5: Delta evaluation -- RandomDayOff(nurse n, working day d)
// Sets sched[n][d] = 0 (day off); reverts after delta measurement.
// Complexity: O(N + D)
// ============================================================
static int deltaRandomDayOff(const Problem& prob,
                              std::vector<std::vector<int>>& sched,
                              int n, int d)
{
    int old_partial = coverageCostDay(prob, sched, d)
                    + nurseCostFull(prob, sched, n);

    const int old_shift = sched[n][d];
    sched[n][d] = 0;

    // Hard coverage check: reject if day-off creates any demand deficit on day d
    int new_cov = coverageCostDay(prob, sched, d);
    if (new_cov > 0) {
        sched[n][d] = old_shift; // revert
        return 999999;
    }

    int new_partial = new_cov
                    + nurseCostFull(prob, sched, n);

    sched[n][d] = old_shift; // revert

    return new_partial - old_partial;
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
            int c = nurseCostFull(prob, tmp, n);
            if (c > max_nurse_cost) max_nurse_cost = c;
        }
        // Alternating Night(3)/Early(1): maximises forbidden successions
        for (int d = 0; d < prob.num_days; d++)
            tmp[n][d] = (d % 2 == 0) ? 3 : 1;
        int c = nurseCostFull(prob, tmp, n);
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
//   70% TwoWaySwap  -- swap two nurses on one day
//   30% RandomDayOff -- assign day off to one nurse on one working day
// ============================================================
nlohmann::json runHeuristic(const nlohmann::json& data) {
    Problem prob          = parseProblem(data);
    auto    sched         = prob.schedule;
    const int initial_cost = fullCost(prob, sched);

    int  cur_cost  = initial_cost;
    int  best_cost = initial_cost;
    auto best_sched = sched;

    // SA / LA parameters
    const double BETA          = 0.9;
    const int    COOL_EVERY    = 30000;
    const double T_MIN         = 10.0;
    const int    NO_IMPROVE_MAX = 500000;
    const int    GAMMA         = 150;

    double T = computeT0(prob, sched);

    // Late Acceptance circular buffer
    std::vector<int> la_list(GAMMA, cur_cost);

    std::mt19937 rng(42);
    std::uniform_real_distribution<double> uni01(0.0, 1.0);
    std::uniform_int_distribution<int>     nurse_dist(0, prob.num_nurses - 1);
    std::uniform_int_distribution<int>     day_dist(0, prob.num_days - 1);

    long long iter        = 0;
    int       no_improve  = 0;

    while (T > T_MIN && no_improve < NO_IMPROVE_MAX) {

        int delta = 0;
        bool move_valid = false;
        int op_n1 = -1, op_n2 = -1, op_d = -1; // TwoWaySwap params
        int doff_n = -1, doff_d = -1;            // RandomDayOff params
        bool use_dayoff = (uni01(rng) >= 0.70);

        if (use_dayoff) {
            // RandomDayOff: pick nurse, collect working days, pick one
            int n = nurse_dist(rng);
            std::vector<int> working;
            for (int d = 0; d < prob.num_days; d++)
                if (sched[n][d] != 0) working.push_back(d);
            if (!working.empty()) {
                std::uniform_int_distribution<int> wd(0, (int)working.size() - 1);
                int d = working[wd(rng)];
                delta      = deltaRandomDayOff(prob, sched, n, d);
                doff_n     = n;
                doff_d     = d;
                move_valid = true;
            }
        }

        if (!move_valid) {
            // TwoWaySwap (also fallback when no working day found for DayOff)
            int n1 = nurse_dist(rng);
            int n2 = nurse_dist(rng);
            while (n2 == n1 && prob.num_nurses > 1) n2 = nurse_dist(rng);
            int d  = day_dist(rng);
            delta  = deltaTwoWaySwap(prob, sched, n1, n2, d);
            op_n1  = n1; op_n2 = n2; op_d = d;
            move_valid = true;
        }

        // Acceptance: improvement OR Late Acceptance OR Metropolis
        const int  la_ref  = la_list[iter % GAMMA];
        const bool accept  = (delta < 0)
                          || ((cur_cost + delta) < la_ref)
                          || (uni01(rng) < std::exp(-static_cast<double>(delta) / T));

        if (accept) {
            if (doff_n >= 0) {
                sched[doff_n][doff_d] = 0;
            } else {
                std::swap(sched[op_n1][op_d], sched[op_n2][op_d]);
            }
            cur_cost += delta;

            if (cur_cost < best_cost) {
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

    nlohmann::json result = data;
    result["current_schedule"]          = best_sched;
    result["metadata"]["initial_cost"]  = initial_cost;
    result["metadata"]["final_cost"]    = best_cost;
    return result;
}
