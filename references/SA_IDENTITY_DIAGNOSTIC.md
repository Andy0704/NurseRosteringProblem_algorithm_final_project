# SA ≡ Evaluator 同源诊断链（落盘记录）

<!-- 用途：跨 session 交接的核心资产。本文件记录「SA cost function 与 penalty_evaluator 同源化」 -->
<!-- 这条诊断线从 ratio 误诊到逐项同源的完整推理，丢失需重推多轮。执行切三段，中途至少两次交接。 -->

## 最终结论（一句话）

SA 与 evaluator 的成本差异**纯属实作漂移，无任何加速/多目标设计意图**。
正确做法是让 SA 逐项重写为与 evaluator 同源（计算同一个 INRC-II 真实加权惩罚），
**不是**验证序保持、**不是**对齐数字尺度、**不是**包装成 objective design。
文献（Turhan & Bilgen 等主流 IP+SA matheuristic）的标准即两层共享同一目标函数；
delta evaluation 是「同一目标函数的 O(1) 精确增量」，不是替代的代理成本。

---

## 诊断链演进（为什么走到「同源」这个结论）

1. **现象**：SA initial_cost 远大于 milp_obj，n012w8 ratio 3.65–12.92，n021w4 6.25–9.75。
2. **第一次修正**：SA 的 num_assignments 用全 4 周合约边界，MILP 用按周摊分 → 改为按周。
   结果 n012w8 ratio 落到 2.0–2.6 ✓，但 n021w4 仍 5–9 ✗。
3. **关键判读**：同一修正一个实例有效一个无效 → n021w4 残差**不是** assignment 尺度，
   是**第二个、不同性质**的漂移（window-sum vs run-length），被第一次诊断混在一起。
4. **方向确认**：ratio 是**伪指标**。即使 ratio≈1 也不证明同源；正确标准是
   **逐项 per-solution 精确相等（<1e-6）**。「数字相等无意义，只需排序/同源」经确认后，
   进一步确认根本不该有两个函数 → 修回同源。

---

## 三个结构性漂移源（SD-1/2/3）+ carry-in

| 编号 | 漂移 | SA 现状 | evaluator 现状 | 修法 |
|---|---|---|---|---|
| SD-1 | open-run 评分 | loop 内每个工作日算 max-excess（含 d=6）+ post-loop check | 从不评 open run，延迟到下周（`range(6)`，day 6 永不 run-end） | 改 transition-based：只在 run 结束（work→off）时评分 |
| SD-2 | min-violation 权重 | flat `CONSEC_WEIGHT` | 比例 `(min − run_len) × _W_CONSEC` | 改比例公式 |
| SD-3 | consecutive same-shift block | SA-only（heuristic.cpp 274–291） | 无 | 整块删除 |

**权重核对**：`_W_CONSEC=15`，S2/S3 共用。SA `CONSEC_WEIGHT=15` **已正确，不需改**。
（早期 draft 误判 off 该用 30，已证伪。）

**loop 范围**：SA `d < 7`，evaluator `range(6)`。删 post-loop **不够**，loop 本身要改
（否则 d=6 仍在 loop 内多算 open run）。

**Carry-in 互斥前提（已实测，非假设）**：
扫描 51 个 H0 文件、2994 笔 nurse-history → consecutive_working_days 与
consecutive_days_off **0% 同时 > 0**（35.4% work-only / 64.6% off-only）。
故 SA 用布尔代理 `hist_consec_work == 0` 推断 off carry-in 成立。
**这是一次性 gate**：若未来 instance 违反互斥，SA 会静默少加 carry-in，需改用实际值。

---

## ⚠️ 未解决：forbidden succession 的 total 归属矛盾（动手前必须定性）

逐项拆分后浮现的**最后一个结构性同源问题**：
- evaluator 的 `_compute_forbidden_successions` 返回 raw count，**且不进 evaluate() total**。
- SA 的 `nurseCostFull` 用 `FORBIDDEN_WEIGHT=25` 把 forbidden **算进 total**。
- 后果：两层 total **结构性不可能相等**，即使 S1/S2/S3/S4 全同源。

**「只比 forbidden count」绕过了这个矛盾，没有解决它。** 这是病根（两层对「什么该进目标」
定义不一致）的又一化身。动手前必须定性：

- **若 forbidden 是 hard（比照 MILP H3=0）** → SA 不应将 25×forbidden 计入 total
  （改 hard check 或排除），total 才能对齐。
- **若 forbidden 是 soft** → evaluator 漏算，应修 evaluator 纳入 total，两边同权。

---

## 其他已知 divergent（本轮标记、不 block）

- **S1 coverage**：已知未同源（属 hard coverage check 独立线），identity test 不 assert，仅 log。
- **S4 preferences**：SA `SHIFT_OFF_REQ_W=5` vs evaluator `_W_PREF=10`（factor 2 分歧）。
  本轮标 known-divergent，记录违规数，待后续处理。

---

## 验证标准（铁律）

1. **逐项断言，不用聚合**：S1/S2/S3/S4/forbidden 各自比对，禁止合并成单一 total 比
   （否则未验证项的分歧会伪装成 consec 改坏，重蹈 S1 混入覆辙）。
2. **per-solution 精确相等 <1e-6**，已知 divergent 项（S1/S4）除外。
3. **绝不用 ratio fallback** 凑过关。任一 block 项失败 → 立即停、打印两边分项 breakdown、
   不继续。
4. **随机解负责广度，手工 case 负责 carry-in 深水区**：N=200 随机解几乎触发不到
   carry-in 路径，必须用确定性 case（CW-1..4、CW-min、CO-1..3、Boundary、cross-week 接续）
   覆盖每条 carry-in 分支。

---

## 执行计划（切三段，禁止一次跑完）

理由：plan 约 350 行，单次执行有中途自行修正、token 耗尽断线风险（前有跑一半断线先例）。

- **段1（只读，零风险）**：确认 Component Source Analysis + 互斥扫描属实 + forbidden 定性。
  不写代码，report 后停。
- **段2（改 + 窄验证）**：Change A/B/C + NurseCost 结构体 + `--eval-only`，
  只跑 10 个确定性 carry-in case。全过 report 停，**先不跑 800 随机解**。
- **段3（广度）**：确认段2全过后，跑 800 随机解 + pipeline smoke test。
每段自停回报，等确认再下一段。

---

## 后续顺序（同源完成后）

1. hard coverage check（return 999999）是否锁死 SA —— **必须等同源后才能判断**
   （现在 cost 还漂，分不清 SA 不动是被锁死还是误判）。
2. S4 weight 5 vs 10、forbidden total 归属 —— 同源收尾。
3. **look-ahead 跨周机制** —— 这才是研究主战场（非 bug fix），对应 benchmark S3 与
   sequence-dependent cost niche。此时才该重开 autorc + autoresearchclaw。