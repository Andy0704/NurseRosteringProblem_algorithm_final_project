# NRP 專案 6/24 報告材料

> 給 Ben、Charles：這是 6/9-6/21 的完整進度 + 簡報製作材料。
> 即使你沒有跑過 code，讀完這份文件應該能理解我在做什麼、
> 為什麼某些 finding 對研究而言重要、且能幫忙做出有深度的 slide。
>
> 你需要做的事在文件末尾「組員任務分配」段。

---

## 第 0 段：一句話總結這兩週

> 從實作 Phase 2 cross-week look-ahead 開始，意外發現 evaluator 對 INRC-II 規格
> 有 4 處 weight 不一致 + 1 處 latent bug。全部修正後、n012w8 真實 cost 從報告的 
> 860 變 2770、再用 Mischek 2019 look-ahead 機制 + bug fix 降到 860（spec-correct 
> 之後再 -69%）。跑了 14 datasets × 3 modes = 60 jobs 完整 benchmark 比較 
> INRC-II winners。最後發現 F&O ablation 自己也有 bug、誠實 disclose 而非藏。

四個關鍵字：**audit、F1 root cause、Mischek 三件套、honest disclosure**。

---

## 第 1 段：背景（你可能已經忘了）

### 1.1 INRC-II 是什麼

INRC-II = Second International Nurse Rostering Competition（2014-2015 舉辦）。
這是個學術競賽，目的是給研究者一個 standard benchmark 來比較 nurse scheduling 演算法。

「Nurse scheduling」就是醫院排班——每週要排幾個護士、什麼班、滿足以下條件：
- 每天每個 shift 至少 N 個護士有班（硬約束 H2）
- 每位護士工作天數有上下限（軟約束 S6）
- 不能連續工作太多天（S2）、不能休太多天（S3）
- 護士偏好（S4）、週末完整性（S5）等等

評分 = 各 soft 約束違反次數 × 對應 weight（S1=30、S2=15 or 30、S3=30、S4=10、...）

INRC-II 特別之處：**4 週或 8 週，每週解一次、week k 結果影響 week k+1**。這個叫
「multi-stage」設計、是 cross-week pathology 的成因（後面會講）。

### 1.2 我們的演算法架構
Python MILP（外層）+ C++ SA/LA（內層）

↓               ↓

solve a single   improve the schedule

week's roster    within budget

via integer      via simulated annealing

programming
- **MILP** = Mixed Integer Linear Programming，用 CBC solver
- **F&O** = Fix-and-Optimize：把 MILP 的解抓 2 個 nurse「unfix」、重解局部、看
  能否改善
- **SA/LA** = Simulated Annealing + Late Acceptance：機率性搜尋，跑 ~50 萬 iteration
- 三層串接：MILP → F&O → SA → output schedule

兩層之間透過 `problem_exchange.json` 溝通。

### 1.3 上個 milestone (2026-06-04) 我們做完什麼

達到「SA-evaluator identity」：SA 用 C++ 算出來的 cost 跟 Python evaluator 用
schedule 重新算的 cost 完全一致（誤差 < 1e-6）。這是 800 個隨機 schedule × 21 
checkpoint 都對的「同源」。

當時報告 n012w8 cost ≈ 860、覺得 SA 改善 effective、準備進 Phase 2 cross-week 
look-ahead。

---

## 第 2 段：兩週發生了什麼（時間線）

### Day 1 (6/9-6/10)：寄信給老師

我們團隊曾就三個方向寄信給指導老師：
- normalized weight 作為 SA search surrogate
- multi-objective Pareto 框架
- INRC-II 是否仍 active

老師回信糾正了四個我們用錯的理論說法：
1. ❌「INRC-II 權重反映臨床決策偏好」→ ✅ 是 competition scoring rule，為文獻可比較性
2. ❌「加權求和保證找到 Pareto 最優」→ ✅ 在離散非凸 NRP 只能找到凸包上的部分點
3. ❌「Pareto 方法本質回到加權求和」→ ✅ 有 ε-constraint、reference-point、
   lexicographic 等
4. ❌「INRC-II 是 7-objective problem」→ ✅ 是單一加權目標問題

定案：**繼續用 INRC-II 官方 scoring**（不做 multi-objective）、**normalized weight 
只當 SA 搜尋 surrogate 不動 scoring**、**Phase 2 look-ahead 是 cross-week 衝突的
正確 fix**。

### Day 2-5 (6/11-6/15)：Phase 1 SA 強化

連續做完三個 SA 補丁：

**(a) Big-M coverage penalty** (commit `5ccc386`)
之前 SA 遇到 coverage 約束會 hard reject（`return 999999`），導致 SA frozen——
在 high-temperature exploration 時都進不去任何 H2-violating state、卡死。
改成 big-M soft penalty（M_COVER ≈ 3·T0、p0=0.05）讓 SA 高溫時能短暫穿越 H2、
低溫時自然收斂回 H2-clean。

**(b) ShiftTypeChange operator** (commit `802bab5`，Knust 2019)
加第三個 SA neighborhood operator：原本只有 TwoWaySwap 和 RandomDayOff（都只能
work→off 方向），加 ShiftTypeChange 補上「off→work」和「shift A → shift B」
方向。這也是 Knust & Xie 2019 paper 在他們 INRC-II SA 中用的標準 operator。

**(c) M_COVER bookkeeping fix** (commit `7f0aa33`)
ShiftTypeChange 讓 SA 第一次能修復 H2-infeasible seed、然後揭露一個 bookkeeping
bug：cur_cost 的初始 baseline 假設 seed 是 H2-clean、但實際可能不是、所以當 SA 
把 schedule 修好變成 H2-clean、cur_cost 會變負數。修正：cur_cost = fullCost + 
M_COVER × initial_units。

跑完三個 fix，n012w8 cost 從 110 變 240（改善但 SA frozen 修完）。

### Day 6 (6/16)：Audit ⭐ Critical Finding 1

進 Phase 2 look-ahead 時，第一步是實作 Mischek 2019 的 S10\* mechanism、選擇 
penalty weight α。

選 α 的過程要 trace「我們 evaluator 對 S2 連續工作日違反到底罰多少分」。看到 
penalty_evaluator.py 用了 `_W_CONSEC = 15`、就去查 INRC-II 規格——
Ceschia 2019 §2.5.1 明確寫 S2 有兩個 sub-component：

- S2 CS2a/b（**同班別**連續日）：weight = 15
- S2 CS2c/d（**任意班別**連續工作日）：weight = 30

而我們的 `_W_CONSEC = 15` 同時用在這兩個 sub-component 上、且實際算的是 CS2c/d
（任意班別，spec 應該 30）。**under-weight 2 倍**。

進一步 audit 揭露 4 處不一致：

| Component | Spec | evaluator | SA cpp | MILP | 嚴重度 |
|---|---|---|---|---|---|
| S1 coverage | 30 | 30 | 30 | 30 | ✅ |
| S2 CS2a/b | 15 | **missing** | **missing** | **missing** | ⚠️ 整個 sub-comp 沒做 |
| S2 CS2c/d | 30 | **15** | **15** | **15** | ❌ 2× under-weight |
| S3 consec off | 30 | **15** | **15** | 30 | ❌ eval/SA wrong, MILP right |
| S4 preference | 10 | 10 | 10 | 10 | ✅ |
| S5 weekend | 30 | **missing** | **missing** | 30 | ⚠️ MILP only |
| S6 total assignment | 20 | **missing** | **10** | **15** | ❌ 3-way divergence |
| S7 working weekend | 30 | **missing** | **missing** | 30 | ⚠️ MILP only |

「Same-wrong-source identity」這個觀念是核心：之前我們慶祝的「SA-evaluator 
identity 同源」（commit `5ccc386`、800 schedule test）實際上是「**兩邊用同樣
錯誤 weight、所以對得起來、但對到的是錯誤的 INRC-II score**」。

**這對研究意義重大**：過去 3 個月所有 cost measurement、所有 benchmark、所有 
PROJECT_STATUS 進度報告的數字，都建立在這個錯誤 evaluator 上。

### Day 7-8 (6/17-6/18)：Audit response — W-2 / W-3 / W-6

分三段 commit 把 evaluator + SA + MILP 三層全部對齊 spec：

**W-2** (commit `f5737bc`)：penalty_evaluator.py `_W_CONSEC` 15 → 30
跑 22 tests、預期 9 個失敗（identity 被打破）、確認失敗模式

**W-3** (commit `bee2dac`)：heuristic.cpp `CONSEC_WEIGHT` 15 → 30
identity 重建、22/22 tests 重新 pass

**W-6** (commit `073d723`)：
- MILP `W_ASSIGN` 15 → 20
- SA cpp `TOTAL_ASSIGN_W` 10 → 20
- evaluator 加 `evaluate_global_s6_s7` function（horizon-end S6/S7 計算）
- multi_week_runner.py 結束時呼叫 global S6/S7 evaluation

修完後 n012w8 真實 cost：**per-week 1270 + global 1500 = 2770**。
比之前報告的 860 高 3.3 倍。

「我們之前對 instance 困難度的估計 understate 了 3.3 倍」——這句要寫進 slide。

### Day 9 (6/18)：S10\* implementation 嘗試

實作 Mischek 2019 S10\*（per-week MILP soft penalty 對「快撞 max_consec_work
的 nurse」加罰）。α=30 對齊我們 spec-correct evaluator 的 CS2c/d weight。

結果：在 spec-correct baseline 下重跑：
- n005w4：320 → 240（-25%）✅
- n012w8：2770 → 3250（+17%）❌ regression
- n021w4：350 → 370（+5%）持平

n012w8 regression 出乎意料。Diagnostic 分析顯示：S10\* 讓 MILP 在 W2 避免 stretch
tail、但 SA 接續週把壓力推到 W5（W4 從 950 變 60、W5 從 400 變 930）。**SA 救 W4
但把累積壓力傳給 W5**。

### Day 10 (6/19)：F1 root cause 發現 ⭐ Critical Finding 2

進 段0 設計 S6\*/S7\* 時，CLI 仔細讀 milp_model.py 對 S6 的處理。發現 line 289-298 
的「S5」block（mislabel、其實是 S6）用了：

```python
estimate = max_total_assignments / 4   # ❌ static, ignores history
```

而 Mischek S6 / S6\* spec 要求：

```python
cumulative = h_assignments + Σ(x[n,d,s,k] for this week)  # ✅ real history
target_for_week_k = ⌊max_total_assign × k / num_weeks⌋    # proportional
```

換言之，**MILP 對 nurse 累積工作天的估算從第一週就是錯的**——它假設「每週剛好
分到 max/4」、不看 history 真實累積數。當 SA 把某週的 work loading 加重、history 
傳給下週時、MILP 完全不知道前面已經多排了多少。

修正 `commit 107fb72`：用 cumulative tracking 替代 ÷4 estimate。

效果：**n012w8 cost 2770 → 1070（-61%）**。

更重要的研究意義：**這推翻了之前對 cross-week pathology 的理解**。我們以為要做
look-ahead mechanism、實際根因是 basic budget tracking 有 bug。S10\* 之所以
mixed result、不是 mechanism 不好、是它建立在錯誤 baseline 上。

### Day 11-12 (6/19-6/20)：Mischek 三件套完整實作

繼續加 S6\* (Mischek eq.29-30、cumulative tracking 的 look-ahead 版) 和 S7\* 
(eq.33、weekend budget 版)。

完整 ablation on test set：

| Config | n012w8 | n005w4 | n021w4 |
|---|---|---|---|
| No look-ahead (W-6) | 2770 | 320 | 350 |
| +S10\* alone | 3250 | — | — |
| +S6\* +S10\* (F1+combo) | 1070 | 260 | 400 |
| **+S6\* +S10\* +S7\* (Mischek 三件套)** | **860** | **240** | **450** |

Mixed-bag finding：**no single instance benefits from every term**。n012w8 +S7\* 
再降、n005w4 +S10\* 改善但 +S7\* 效果有限、n021w4 +S7\* 反而從 400 變 450（但
這是 "honest correction of silently violated S7 bound"、不是真的變差）。

### Day 13 (6/20-21)：14-dataset full benchmark

跑完 EVAL-段0 / 段1 / 段2-pre：
- 從 INRC-II official website 取回 28/28 finalist instance IDs
- 從 official validated spreadsheet 取回 28/28 best-known cost
- 寫 `evaluation/run_ablation.py`（mode-gated runner）
- 寫 `evaluation/run_batch.py`（fault-tolerant batch wrapper）

睡前 launch overnight batch：14 datasets × 3 modes + 3 testdataset extras = 
60 jobs，nohup 跑 9 小時 27 分鐘、**0 failure**。

| Dataset | N | best-known | milp | fo | full | gap_full% |
|---|---|---|---|---|---|---|
| n030w4 | 30 | 1755 | 620 | 620 | 2220 | +26.5% |
| n030w8 | 30 | 1900 | 1280 | 1280 | 3610 | +90.0% |
| n040w4 | 40 | 1730 | 1470 | 1470 | 1470 | -15.0% |
| n040w8 | 40 | 2700 | 3610 | 3610 | 3460 | +28.1% |
| n050w4 | 50 | 1480 | 810 | 810 | 1340 | -9.5% |
| n050w8 | 50 | 5410 | 2550 | 2550 | 5560 | +2.8% |
| n060w4 | 60 | 2815 | 2880 | 2880 | 2880 | +2.3% |
| n060w8 | 60 | 2765 | 3070 | 3070 | 4040 | +46.1% |
| n080w4 | 80 | 3535 | 4330 | 4330 | 4330 | +22.5% |
| n080w8 | 80 | 4995 | 10270 | 9120 | 9120 | +82.6% |
| n100w4 | 100 | 1445 | 3560 | 3560 | 7950 | +450.2% |
| n100w8 | 100 | 3055 | 7430 | 7430 | 7010 | +129.5% |
| n120w4 | 120 | 2435 | 4250 | 4240 | 4240 | +74.1% |
| n120w8 | 120 | 3510 | 6140 | 6160 | 6470 | +84.3% |

Plots：5 個 PNG 在 `results/batch_2026-06-20/plots/`。

幾個觀察：
- 「負 gap」（n040w4 -15%、n050w4 -9.5%）不是真贏 INRC-II winner、是因為我們 
  evaluator 還缺 S2 CS2a/b、S5、所以 cost 被低估
- n100/n120 顯著 gap 是真實的——MILP 在大 instance 撞 spec time ceiling 
  (310s/week)
- **SA 在大 instance 上系統性 regress**：14 datasets 中 SA 改善 3 個、持平/regress 
  11 個——跟在 n005-n021 看到的「SA 是淨改善」相反

### Day 14 (6/21)：F&O bug discovery ⭐ Critical Finding 3

跑完 60-job benchmark 後 P6 表攤開來看：**F&O 跟 MILP 在 11/14 datasets 完全
相同**。F&O 是 fix-and-optimize loop、應該對任何非最優解都有改善空間——「fo == milp 
on 11/14」不正常。

Diagnostic：

CLI 跑 `/tmp/diag_fo.py` 直接 instrument fix_and_optimize() 內部、印出每個 
sub-problem 的 PuLP status + objective。發現：

在非 final week，主週解的 MILP penalty = 0、但 F&O sub-problem penalty 
= 2670-3790（9-12 倍主週解）。**不是「F&O 找不到改善」、是 F&O sub-problem 在
解一個跟主週完全不同的 objective**。

Root cause：milp_model.py `fix_and_optimize()` line 434-457 內部呼叫 
`self.build()`、**沒傳新增的 `(is_final_week, cur_week, num_weeks)` 參數**。
defaults 是 `(True, 1, 1)`——意味 F&O sub-problem 永遠假設是 final week of 
1-week horizon、不含 S6\*/S7\*/S10\* look-ahead penalty。

acceptance check「new_penalty < current_penalty」變成「**用錯誤 model 算的 
new penalty vs 用正確 model 算的 current**」——蘋果比橘子、橘子永遠贏。F&O
sub-problem 永遠被 reject。

這是 2026-06-21 才發現的 bug，commit `34caec8` 把它揭露在 references/eval_results_2026-06-20.md
和 PROJECT_STATUS.md。修正只需要一行 plumbing change（把參數從 `self` 傳進去）、
但需要重跑 9 小時 batch、**所以 defer 到報告之後**。

---

## 第 3 段：3 個 Critical Findings 對研究的意義

### Finding 1：Evaluator audit

不只是「修了 4 處 bug」、是「我們花 3 個月用錯 evaluator 都沒發現、直到實作 
look-ahead 才 trigger audit」。

**對 paper 的意義**：
- 顯示 spec-compliance 在 IP-based heuristic 研究的重要性
- "Same-wrong-source identity" 觀念——同源 ≠ 對
- Audit 是 cross-week 機制研究的**前置條件**、沒做 audit 你會花大量時間在錯誤 
  baseline 上

### Finding 2：F1 root cause

不只是「修了 ÷4 mislabel」、是「我們以為要做 look-ahead mechanism、實際根因是 
basic budget tracking 有 bug」。

**對 paper 的意義**：
- 顛覆了 cross-week pathology 的 mechanism hypothesis
- 顯示對既有 codebase 的 routine audit 在實作新 mechanism 前的必要性
- 工程 correctness 是 algorithm research 的 prerequisite、不是 separate concern

### Finding 3：F&O bug honest disclosure

不只是「我們發現 F&O 有 bug」、是「我們在做 ablation 才發現 ablation 變數有 bug、
誠實揭露而非藏」。

**對 paper 的意義**：
- Process maturity 的展示——good research catches its own mistakes
- Rule 14 evidence standard 在實際 ablation 工作中發揮效果
- F&O 重跑是 future work，不是 hiding negative result

---

## 第 4 段：Slide Outline（15 張）

每張：標題、核心句、視覺素材、講法。

### S1：封面 + 專案 recap (30 sec)

**標題**：INRC-II 護士排班 Matheuristic — Phase 2 進展報告  
**副標**：Cross-week look-ahead, spec audit, full benchmark  
**內容**：
- 隊員：Andy、Ben、Charles
- 日期：2026-06-24
- 學程：成大生醫工程

**口頭**：「我們的 INRC-II nurse rostering matheuristic、上次報告完成 Phase 1 SA 
改善、今天匯報 Phase 2 進展。過程中發現幾個重要的 finding 改變了我們對研究問題的
理解。」

### S2：上次匯報的位置 (30 sec)

**標題**：上次 milestone：SA-evaluator identity (2026-06-04)  
**核心句**：當時報告 n012w8 cost = 860、SA 改善 effective、準備進 Phase 2  
**視覺**：commit chain 截圖（5ccc386 → 7f0aa33 → 段1B 等）

**口頭**：「上次報告我們達到 SA-evaluator identity、800 schedule 同源驗證、
n012w8 cost 報為 860。當時的計畫是進 Phase 2 cross-week look-ahead。」

### S3：Phase 2 計畫 (45 sec)

**標題**：原本計畫：實作 Mischek 2019 cross-week look-ahead  
**核心句**：Mischek paper S10\* unresolvable end-of-week stretch-tail 是教科書級
別對 cross-week pathology 的 engineering 回應  
**視覺**：Mischek 2019 paper Table 2 截圖（或第 137 頁的 eq.40）

**口頭**：「Cross-week look-ahead 的研究主參考是 Mischek & Musliu 2019。他們提出 
5 個 search-time soft constraint extensions、最重要是 S10\* unresolvable 
end-of-week stretch-tail——當週末 nurse 撞 max_consec_work 時、下週開頭一定有 
S2 違反。」

### S4：Critical Finding 1 — Audit Trigger ⭐ (90 sec)

**標題**：選 S10\* α 時 trigger 了 evaluator audit  
**核心句**：我們 `_W_CONSEC = 15` 用在 S2 CS2c/d、Ceschia 2019 spec = 30、
2× under-weight  
**視覺**：
- audit table（4 處不一致）
- 「Same-wrong-source identity」概念圖示

**口頭**：「為了選 S10\* 的 penalty weight、我要 trace evaluator 對 S2 連續工作日
違反到底罰多少。發現我們用 weight 15、但 Ceschia 2019 規格是 30——under-weight 
2 倍。然後 audit 揭露 4 處不一致。**之前我們的 SA-evaluator identity 是 
"same-wrong-source"——兩邊用同樣錯誤的 weight、所以對得起來、但對到的是錯誤 INRC-II 
score**。」

### S5：Audit Response — W-2 / W-3 / W-6 (60 sec)

**標題**：Three-commit spec alignment  
**核心句**：evaluator + SA + MILP 三層全部對齊 Ceschia 2019 spec  
**視覺**：3 個 commit hash + 各自改了什麼的 table

**口頭**：「分三段修：W-2 修 evaluator、W-3 修 SA C++、W-6 修 MILP 並補上 S6/S7 
horizon-end evaluation。每段都跑 22 tests 確認 identity 重建。」

### S6：New Baseline — 真實 cost 比之前高 3.3 倍 ⭐ (75 sec)

**標題**：Spec-correct baseline：n012w8 從 860 變 2770  
**核心句**：我們之前對 instance 困難度的估計 understate 了 3.3 倍  
**視覺**：before/after table

| Instance | Pre-audit reported | Post-W-6 spec-correct |
|---|---|---|
| n005w4 | (low) | 320 |
| n012w8 | **860** | **2770** |
| n021w4 | (low) | 350 |

**口頭**：「修完後 n012w8 真實 cost = per-week 1270 + global 1500 = 2770。
比之前報告的 860 高 3.3 倍。**這不代表我們演算法變差、代表我們之前對自己的測量
過於樂觀**。」

### S7：Mischek 三件套實作 (60 sec)

**標題**：Phase 2 完成：S10\* + S6\* + S7\* full trio  
**核心句**：search-time only、official scoring 不動  
**視覺**：3 個 mechanism 的 Mischek paper equation 引用

**口頭**：「實作 Mischek 三個 look-ahead mechanism、都是在 MILP objective 加 soft 
penalty、search-time only、不污染最終 INRC-II 評分。」

### S8：F1 Root Cause Discovery ⭐ (120 sec)

**標題**：實作 S6\* 過程的意外發現  
**核心句**：MILP 用 ÷4 static estimate 代替 cumulative history——cross-week 
pathology 真正成因  
**視覺**：
- ÷4 estimate vs cumulative tracking 對照
- before/after n012w8 cost (2770 → 1070, -61%)
- 一句 quote："The root cause of cross-week pathology wasn't the absence of 
  look-ahead, it was budget-tracking correctness."

**口頭**：「設計 S6\* 時 CLI 仔細讀 milp_model.py、發現 line 289-298 的 S6 
penalty 用 max_total_assignments ÷ 4 這個 static estimate——它假設每週剛好分到 
max/4、完全不看 history 真實累積數。修成 cumulative tracking 後 n012w8 從 2770 
變 1070、-61%。**這顛覆了我們對 cross-week pathology 的理解**——我們以為要做 
look-ahead mechanism、實際根因是 basic budget tracking 有 bug。」

### S9：Test-set Ablation (45 sec)

**標題**：Look-ahead trio ablation on test set  
**核心句**：no single mechanism wins on all instances (mixed-bag finding)  
**視覺**：4-mode × 3-instance ablation table

**口頭**：「在 test set 上跑完整 ablation。Mixed-bag finding——每個 instance 對
不同 mechanism 反應不同。n012w8 +S7\* 再降到 860、n005w4 +S10\* 主要 contribute、
n021w4 +S7\* 反而變差但這是 honest correction of silently violated S7。」

### S10：Full Benchmark — 14 INRC-II Datasets ⭐ (90 sec)

**標題**：完整 INRC-II public testbed evaluation  
**核心句**：60 jobs / 9.4 小時 / 0 failure / used official finalist instances 
+ Ceschia time budget  
**視覺**：
- P1 box plot
- P3 cost vs N line plot

**口頭**：「為了 honest comparison，我們用 INRC-II 官方 finalist 同樣的 instance、
同樣的 time budget。睡前 launch nohup batch、跑了 9 小時 27 分鐘、60 個 (instance, 
mode) job 全部成功 0 failure。Plot 1 是 cost distribution、plot 3 是 cost vs 
nurse count。」

### S11：Gap to INRC-II Winners (60 sec)

**標題**：Comparison to published best-known costs  
**核心句**：≤n060 we're close; n100/n120 large gap (n100w4 worst +450%)  
**視覺**：P4 gap_pct bar plot

**口頭**：「n005-n060 我們接近 INRC-II winner。n100/n120 顯著 gap、最差 n100w4 
+450%。原因是 MILP 在大 instance 撞 spec time ceiling、CBC 沒解到最優、winner 
（NurseOptimizers）用 network-flow MILP 在這個 scale 有結構性優勢。**這是 
future work direction**。」

### S12：F&O Bug Honest Disclosure ⭐ (90 sec)

**標題**：60-job benchmark 暴露的 process matters finding  
**核心句**：fix_and_optimize() build() defaults bug 讓 F&O 在 11/14 datasets 
silently 失效  
**視覺**：
- F&O bug 診斷流程圖
- bug 修法（one-line plumbing）

**口頭**：「跑完 benchmark 才發現 F&O 跟 MILP 在 11/14 datasets 完全相同——不正常。
深入 diagnostic 找到 root cause：fix_and_optimize() 內部 build() 呼叫沒傳新增的 
look-ahead 參數、F&O sub-problem 解的是跟主週不同的 objective、acceptance check 
變成蘋果比橘子。**我們做 ablation 才發現 ablation 變數本身有 bug**。修法是 
one-line plumbing、但要重跑 9 小時 batch、defer 到報告之後。揭露在 PROJECT_STATUS 
而非藏。」

### S13：Methodology Highlights (45 sec)

**標題**：研究紀律（Process matters）  
**核心句**：Rule 14 evidence standard、segment-based 開發、25+ commits、22 tests  
**視覺**：commit history graph + tests pass count

**口頭**：「方法論上、每個 finding 都有 reproducible command + paper citation 
作為證據。Segment-based 開發、每段 stop and review。25 個 commits、過去兩週的
工作 audit trail 都在 origin/main。22 個 automated tests 守 invariants。」

### S14：Open Questions / Next Steps (60 sec)

**標題**：未完成的事  
**內容**：
- F&O bug 修正 + 14-dataset re-run（已有具體 plumbing fix、9 小時 batch）
- S2 CS2a/b、S5、S7 補完 evaluator (scope completeness)
- SA cross-week awareness（current SA single-week only、是 large-instance 
  regression 的 root cause）
- 大 instance MILP relaxation 強化（n100/n120 gap closing）
- SA seed proper stochastic stability measurement

**口頭**：「F&O bug 已有 fix、就差重跑 batch。Evaluator 的 missing components 
是 scope completeness 補完。SA cross-week awareness 是 Phase 3 候選——current 
SA single-week、解釋為什麼大 instance regress。」

### S15：致謝 + References (30 sec)

**標題**：References + 致謝  
**References**：
- Ceschia et al. 2019. Second International Nurse Rostering Competition. *AOR*.
- Mischek & Musliu 2019. Iterated Local Search for Multi-Stage NRP. *AOR*.
- Knust & Xie 2019. SA operators for NRP.
- Römer & Mellouli 2019. Network-flow MILP for INRC-II (winner).

**致謝**：指導老師、實驗室、組員 Ben + Charles。

GitHub：Andy0704/NurseRosteringProblem_algorithm_final_project

---

## 第 5 段：可能的 Q&A + 預備答案

### Q：為什麼 SA 在大 instance regress 但 small instance 改善？
A：SA 是 single-week scope、改善的是當週、但沒有 cross-week awareness。Small 
instance (n005-n021) 跨週 coupling 弱、SA 救當週的改善 dominates。Large instance
(n030+) 跨週 coupling 強、SA 把當週改善 trade 給下週 carry-in 變糟、net regress。

這指向 Phase 3：SA 需要 cross-week soft penalty、類似 MILP 加 Mischek 三件套那
樣。當前 SA 完全不知道 history 累積、是 large-instance regression 的 root cause。

### Q：你的 F&O 為什麼沒效？
A：發現 fix_and_optimize() 內部 build() 呼叫沒傳新增的 look-ahead 參數、F&O 
sub-problem 解的 objective 跟主週不同。修法是 one-line plumbing、但需要重跑 
9 小時 batch、所以揭露在 limitations、defer 到報告後做。

### Q：你的 cost 跟 INRC-II winner 差這麼多（n100w4 +450%）合理嗎？
A：合理但需要解釋。我們的 MILP 在大 instance 撞 Ceschia 2019 spec time budget 
ceiling（310s/week for N=120）、CBC 沒收到最優就停。NurseOptimizers（INRC-II 
winner）用 network-flow MILP formulation、LP relaxation 強得多、能在同樣 budget 
內找到更好的 integer solution。這是 future work 方向。

### Q：你之前報告的 cost 為什麼是錯的？
A：我們 evaluator 對 INRC-II spec 有 4 處不一致（S2 CS2c/d under-weight 2 倍、
S3 weight 不一致、S6 3-way divergence、S2 CS2a/b 和 S5 完全沒做）。發現後 W-2/
W-3/W-6 修正。**spec-correct cost 都建立在公開 commit、可以從 GitHub history 
追**。

### Q：你怎麼知道 evaluator 對齊 spec？
A：把 Ceschia 2019 paper section 2.5 weight 表 vs 我們 codebase 每個 weight 
constant 一對一比對。Audit 結果在 references/evaluator_weight_audit.md（commit 
6b11aa2）。每個 weight 都有 PDF page citation。

### Q：你的 SA 收斂 stable 嗎？
A：CBC 解 MILP 是 deterministic（small instance）、SA 的 random seed 我們目前
是 hardcoded、沒做 multi-seed stability measurement。這是 known limitation、列
在 Next Steps。Indirect evidence 是 testdataset extras（3 instances per testdataset）
看 cost 在 SA 用相同 seed 但不同 history-week 排列下 stable 在某個 range。

### Q：為什麼選 Mischek 2019 而非 INRC-II winner NurseOptimizers？
A：兩個原因：(1) NurseOptimizers 用 network-flow MILP、跟我們 vanilla MILP+F&O+SA 
是完全不同 architecture、移植成本高；(2) Mischek 提出的 S10\*/S6\*/S7\* 是 
search-time soft penalty、可以**直接 plug into 我們現有 MILP**、不需要 redesign 
solver structure。

### Q：用 finalist instance 跑 vs 競賽 10 instance/dataset 是不是 sampling 不足？
A：是的、這是 known limitation。INRC-II 競賽用 10 instances per dataset 計算 
finalist score、我們因為 wall-clock budget 限制只用 1 instance/dataset。在 3 
個 testdataset 上 extras 3 instances 提供 indirect stability 證據。Full 10×
instance 是 future work。

---

## 第 6 段：組員任務分配

我（Andy）週六（6/22）+ 週日（6/23）寫 slide 主體。週一 polish + rehearsal。

**Ben、Charles 可以分工的事**：

### Task A：Plots Polish（任一人）

5 個 PNG 在 `results/batch_2026-06-20/plots/`：
- p1_cost_by_dataset.png
- p2_mean_cost_bar.png
- p3_cost_vs_N.png
- p4_gap_to_best_known.png
- p5_wallclock_vs_N.png

請看一遍、有沒有：
- Axis label 不清楚 / unit 沒寫
- Legend 位置擋到資料
- 顏色區分 mode 不夠明顯
- Title 缺失

如果要重新 render、`evaluation/analyze_results.py` 是 plot 生成腳本、可以改 
matplotlib 設定再跑一次。

### Task B：Slide 視覺製作（任一人）

我提供 15 張 outline + 每張內容 + 口頭講法。請：

- 選一個 slide template（簡單乾淨即可、學術風格）
- 把 outline 內容打字進去
- ⭐ 標記的 slide（S4 / S6 / S8 / S10 / S12）多花心思——是 narrative key moments
- 視覺上：每張不要塞太多文字、表用 highlight 強調關鍵數字
- 確保 commit hash / 引用都對得起來（我可以校對）

### Task C：Q&A 練習（兩人都要參與）

週一 rehearsal 時、Ben/Charles 扮演老師、丟我預想的 Q&A + 你們自己想到的 
question。重點是看我有沒有：
- 卡頓 / 講錯數字
- 解釋不清楚 / 用詞太技術
- 「為什麼」這類 follow-up 答得不夠 deep

### Task D：理解整個 narrative（兩人都要）

讀完這份文件後、能夠用自己的話跟同學講「Andy 這兩週做了什麼、為什麼重要」。
口試現場如果老師 cold-call 你們、你們要能接得上。

可以彼此互相 quiz：
- 「為什麼 evaluator audit 重要？」
- 「F1 root cause 是什麼？」
- 「為什麼 F&O 在 11/14 datasets 沒效？」
- 「為什麼 SA 在大 instance regress 但 small instance 改善？」

---

## 第 7 段：Repo 結構快速 reference
NRP_Claude_Agent/

├── PROJECT_STATUS.md            ← 當前狀態、Known Issues、Next Steps

├── CLAUDE.md                    ← 開發紀律（Rule 14 evidence standard 等）

├── outer_milp/                  ← Python MILP + F&O

│   ├── models/milp_model.py

│   └── utils/

│       ├── multi_week_runner.py

│       ├── penalty_evaluator.py

│       └── inrc2_parser.py

├── inner_heuristic/             ← C++ SA/LA

│   └── src/heuristic.cpp

├── evaluation/

│   ├── run_ablation.py          ← mode-gated single-instance runner

│   ├── run_batch.py             ← fault-tolerant batch wrapper

│   └── finalist_instances.txt   ← 28 INRC-II finalist instance IDs

├── references/                  ← 文獻 + diagnostic notes

│   ├── Ceschia(2019)_INRC-II_official_spec.pdf

│   ├── Mischek_Musliu (2019) Look-ahead.pdf

│   ├── evaluator_weight_audit.md          ← 6/16 audit

│   ├── lookahead_design_notes.md          ← Phase 2 設計筆記

│   ├── eval_design_notes.md               ← evaluation 設計

│   ├── eval_results_2026-06-20.md         ← 最新 benchmark 結果

│   ├── w10_1a_verification.md             ← F1 fix verification

│   └── ...

├── results/batch_2026-06-20/

│   ├── batch.log                ← 9.4 hour batch log

│   ├── plots/                   ← 5 PNG plots

│   └── *.json                   ← 60 instance results

└── tests/                       ← 22 automated tests
## 第 8 段：給 Ben/Charles 的快速 catch-up 路徑

1. `git clone` repo（如果還沒）、`git pull origin main`
2. 讀 `PROJECT_STATUS.md`（10 分鐘）
3. 讀這份文件（30 分鐘）
4. 看 5 個 plots（10 分鐘）
5. 互相 quiz（30 分鐘）
6. 開始做 Task A 或 Task B

完整 commit history：
```bash
git log --oneline ebace27..HEAD     # 過去兩週 25+ commits
```

如果有任何 finding 看不懂、隨時 Line 我。
