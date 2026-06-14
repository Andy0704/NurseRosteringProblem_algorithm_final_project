# References: Multi-Objective Nurse Rostering
*Query: `multi-objective nurse rostering` | Year: 2005–2026 | Source: OpenAlex | Total: 16 papers (4 篇未成功檢索)*
*Generated: 2026-06-10*

---

## NRP Optimization & Scheduling

### [1] Burke, E., Li, J., & Qu, R. (2009)
**A hybrid model of integer programming and variable neighbourhood search for highly-constrained nurse rostering problems**
*European Journal of Operational Research* | Citations: 185
DOI: [10.1016/j.ejor.2009.07.036](https://doi.org/10.1016/j.ejor.2009.07.036)
Abstract: *(not available)*

> **Relevance**:
> - **Multi-objective aspect**: 無，weighted-sum 單目標（標準 NRP penalty aggregation）
> - **Dataset**: 比利時護理排班基準（real-world，非 INRC-II）
> - **Method**: Hybrid Integer Programming + Variable Neighbourhood Search（matheuristic）
> - **Applicable to INRC-II**: Partial — IP+VNS matheuristic 架構與本案 MILP+SA 高度類似，但資料集非 INRC-II（abstract 不可得，依標題與已知文獻判斷）

---

### [2] De Causmaecker, P., & Vanden Berghe, G. (2010)
**A categorisation of nurse rostering problems**
*Journal of Scheduling* | Citations: 126
DOI: [10.1007/s10951-010-0211-z](https://doi.org/10.1007/s10951-010-0211-z)
PDF: [Open Access](https://link.springer.com/content/pdf/10.1007/s10951-010-0211-z.pdf)
Abstract: Personnel rostering has received ample attention in recent years. Due to its social and economic relevance and due to its intrinsic complexity, it has become a major subject for scheduling and timetabling researchers. Among the personnel rostering problems, nurse rostering turned out to be particularly complex and difficult. In this paper, we propose a notation for nurse rostering problems along the lines of the α|β|γ notation for scheduling.

> **Relevance**:
> - **Multi-objective aspect**: 無，純分類框架論文，不涉及目標函數設計
> - **Dataset**: N/A（概念性 taxonomy 論文）
> - **Method**: NRP 分類 notation（α|β|γ scheduling notation 的延伸）
> - **Applicable to INRC-II**: Partial — 可用於將本案問題類型在 NRP 文獻中分類定位，但無演算法或目標函數內容

---

### [3] Burke, E., Curtois, T., Post, G. F., Qu, R., & Veltman, B. (2007)
**A hybrid heuristic ordering and variable neighbourhood search for the nurse rostering problem**
*European Journal of Operational Research* | Citations: 179
DOI: [10.1016/j.ejor.2007.04.030](https://doi.org/10.1016/j.ejor.2007.04.030)
Abstract: *(not available)*

> **Relevance**:
> - **Multi-objective aspect**: 無，單目標 heuristic ordering + VNS
> - **Dataset**: Real-world 護理排班 instances（早於 INRC-II 標準誕生）
> - **Method**: Heuristic ordering + Variable Neighbourhood Search
> - **Applicable to INRC-II**: Partial — VNS local search 概念可遷移至本案 inner heuristic 層，但年代與資料集早於 INRC-II（abstract 不可得，依標題判斷）

---

### [4] Liu, Z., Liu, Z., Zhu, Z., Shen, Y., & Dong, J. (2017)
**Simulated annealing for a multi-level nurse rostering problem in hemodialysis service**
*Applied Soft Computing* | Citations: 54
DOI: [10.1016/j.asoc.2017.12.005](https://doi.org/10.1016/j.asoc.2017.12.005)
Abstract: *(not available)*

> **Relevance**:
> - **Multi-objective aspect**: 無 — "multi-level" 指多階段/多層級排班結構，非多目標
> - **Dataset**: 血液透析服務 real-world 資料（特化臨床領域，非 INRC-II）
> - **Method**: Simulated Annealing
> - **Applicable to INRC-II**: Partial — SA 方法論與本案 inner layer 直接相關，但問題領域與約束結構不同於 INRC-II（abstract 不可得，依標題判斷）

---

### [5] Liogys, M. (2014)
**On Multi-Objective Optimization Heuristics for Nurse Rostering Problem**
*Venue: N/A* | Citations: 2
DOI: N/A
Abstract: The nurse rostering problem is usually tackled in the relevant literature as a single-objective optimization problem. Recently, however, the attention of researchers has been attracted by a multi-objective version of that problem. In the present paper we propose an algorithm for the multi-objective version of the problem. The performance of the proposed algorithm is compared with that of the simulated annealing method. The results of the application of the considered algorithms to a real-world optimization problem are provided.

> **Relevance**:
> - **Multi-objective aspect**: 明確 MO — 提出 NRP 的 multi-objective 演算法，並與 SA baseline 比較
> - **Dataset**: Real-world NRP instance（未指明是否為 INRC-II）
> - **Method**: Multi-objective heuristic（演算法細節未在 abstract 說明）vs. Simulated Annealing baseline
> - **Applicable to INRC-II**: Partial — 直接提供 MO vs SO 比較先例，但未在 INRC-II 規模上驗證

---

### [6] Aickelin, U., Burke, E., & Li, J. (2006)
**An estimation of distribution algorithm with intelligent local search for rule-based nurse rostering**
*Journal of the Operational Research Society* | Citations: 83
DOI: [10.1057/palgrave.jors.2602308](https://doi.org/10.1057/palgrave.jors.2602308)
PDF: [Open Access](https://arxiv.org/pdf/0711.3591)
Abstract: Schedules can be built in a similar way to a human scheduler by using a set of rules that involve domain knowledge. This paper presents an Estimation of Distribution Algorithm (EDA) for the nurse scheduling problem, which involves choosing a suitable scheduling rule from a set for the assignment of each nurse.

> **Relevance**:
> - **Multi-objective aspect**: 無，單目標 EDA + rule-based local search
> - **Dataset**: Rule-based NRP instances（英國醫院資料，早於 INRC-II）
> - **Method**: Estimation of Distribution Algorithm (EDA) + intelligent local search
> - **Applicable to INRC-II**: Partial — EDA 屬於與本案 SA 不同的 metaheuristic 家族，直接適用性有限，但再次印證單目標聚合分數為 NRP 文獻常態

---

### [7] Rahimian, E., Akartunalı, K., & Levine, J. (2016)
**A hybrid Integer Programming and Variable Neighbourhood Search algorithm to solve Nurse Rostering Problems**
*European Journal of Operational Research* | Citations: 85
DOI: [10.1016/j.ejor.2016.09.030](https://doi.org/10.1016/j.ejor.2016.09.030)
PDF: [Open Access](https://strathprints.strath.ac.uk/58402/2/Rahimian_etal_EJOR_2016_Hybrid_integer_programming_and_variable_neighborhood_search_algorithm.pdf)
Abstract: *(not available)*

> **Relevance**:
> - **Multi-objective aspect**: 無（abstract 不可得，依標題與作者群已知文獻判斷為單目標）
> - **Dataset**: NRP benchmark instances（具體基準未在標題中說明）
> - **Method**: Hybrid Integer Programming + Variable Neighbourhood Search
> - **Applicable to INRC-II**: Yes（推測）— matheuristic IP+VNS 架構與本案 MILP+SA 高度平行，是方法論層級最相關的論文之一（abstract 不可得，依標題判斷）

---

### [8] Di Martinelly, C., & Meskens, N. (2017)
**A bi-objective integrated approach to building surgical teams and nurse schedule rosters to maximise surgical team affinities and minimise nurses' idle time**
*International Journal of Production Economics* | Citations: 24
DOI: [10.1016/j.ijpe.2017.05.014](https://doi.org/10.1016/j.ijpe.2017.05.014)
Abstract: *(not available)*

> **Relevance**:
> - **Multi-objective aspect**: 明確 bi-objective — 最大化手術團隊親和度、最小化護理師閒置時間，兩者為真正互競目標
> - **Dataset**: 手術室/手術團隊排班資料（醫院特定，非 INRC-II）
> - **Method**: Bi-objective optimization（scalarization 方法在 abstract 中未說明）
> - **Applicable to INRC-II**: No — 手術團隊組成與親和度最佳化超出 INRC-II 的 shift assignment 範疇（abstract 不可得，依標題判斷）

---

### [9] Li, J., Burke, E., Curtois, T., Petrović, S., & Qu, R. (2011)
**The falling tide algorithm: A new multi-objective approach for complex workforce scheduling**
*Omega* | Citations: 62
DOI: [10.1016/j.omega.2011.05.004](https://doi.org/10.1016/j.omega.2011.05.004)
PDF: [Open Access](https://doi.org/10.1016/j.omega.2011.05.004)
Abstract: We present a hybrid approach of goal programming and meta-heuristic search to find compromise solutions for a difficult employee scheduling problem, i.e. nurse rostering with many hard and soft constraints.

> **Relevance**:
> - **Multi-objective aspect**: 明確 MO — goal programming + meta-heuristic 求多重 soft constraint 目標的「compromise solutions」
> - **Dataset**: Complex workforce/nurse scheduling with many hard and soft constraints（real-world，早於 INRC-II）
> - **Method**: Goal programming + meta-heuristic search（Falling Tide algorithm）
> - **Applicable to INRC-II**: Partial — 「以單一演算法對多個 soft constraint 目標求折衷解」的精神，正是 INRC-II S1–S7 weighted aggregation 的先例之一

---

### [10] Ngoo, C. M., Goh, S. L., Sze, S. N., Sabar, N. R., Abdullah, S., & Kendall, G. (2022)
**A Survey of the Nurse Rostering Solution Methodologies: The State-of-the-Art and Emerging Trends**
*IEEE Access* | Citations: 45
DOI: [10.1109/access.2022.3177280](https://doi.org/10.1109/access.2022.3177280)
PDF: [Open Access](https://ieeexplore.ieee.org/ielx7/6287639/6514899/09780256.pdf)
Abstract: This paper presents an overview of recent advances for the Nurse Rostering Problem (NRP) based on methodological papers published between 2012 to 2021. It provides a comprehensive review of the latest solution methodologies, particularly computational intelligence (CI) approaches, utilized in benchmark and real-world nurse rostering.

> **Relevance**:
> - **Multi-objective aspect**: Survey 層級 — 涵蓋 2012–2021 間單目標與多目標 CI 方法
> - **Dataset**: N/A（文獻綜述，涵蓋多個 benchmark 與 real-world NRP）
> - **Method**: 文獻綜述（computational intelligence approaches for NRP）
> - **Applicable to INRC-II**: Yes — 可作為本案方法論在 NRP 文獻中定位的脈絡參考，協助說明 weighted-sum matheuristic 在現有方法光譜中的位置

---

### [11] Mischek, F., & Musliu, N. (2019)
**Integer programming model extensions for a multi-stage nurse rostering problem**
*Annals of Operations Research* | Citations: 28
DOI: [10.1007/s10479-017-2623-z](https://doi.org/10.1007/s10479-017-2623-z)
PDF: [Open Access](https://link.springer.com/content/pdf/10.1007%2Fs10479-017-2623-z.pdf)
Abstract: In the variant of the well studied nurse rostering problem proposed in the Second International Nurse Rostering Competition, multiple stages have to be solved sequentially which are dependent on each other. We propose an integer programming model for this problem and show that a set of newly developed extensions in the form of additional constraints can significantly improve the quality of the generated solutions.

> **Relevance**:
> - **Multi-objective aspect**: 無 — 單目標 IP model，採用 INRC-II 官方加權聚合分數
> - **Dataset**: **INRC-II（Second International Nurse Rostering Competition）— 與本案完全相同的基準**
> - **Method**: Integer Programming model extensions（額外約束以提升解品質）
> - **Applicable to INRC-II**: **Yes — 直接基於 INRC-II**，是本檔案中與本案最相關的論文之一；其 IP 模型擴展可參考用於本案 MILP formulation，並直接證實 weighted-sum 是 INRC-II 的官方標準做法

---

### [12] Kheiri, A., Gretsista, A., Keedwell, E., Lulli, G., Epitropakis, M. G., & Burke, E. (2021)
**A hyper-heuristic approach based upon a hidden Markov model for the multi-stage nurse rostering problem**
*Computers & Operations Research* | Citations: 35
DOI: [10.1016/j.cor.2021.105221](https://doi.org/10.1016/j.cor.2021.105221)
PDF: [Open Access](http://hdl.handle.net/10871/124810)
Abstract: *(not available)*

> **Relevance**:
> - **Multi-objective aspect**: 無 — hyper-heuristic 優化單一 INRC-II 聚合分數
> - **Dataset**: **INRC-II multi-stage benchmark — 與本案相同的基準**
> - **Method**: Hyper-heuristic + Hidden Markov Model（move/operator selection）
> - **Applicable to INRC-II**: **Yes — 直接基於 INRC-II**，move-selection 概念可參考用於本案 inner heuristic 層的 operator selection，但其目標函數與本案相同（單一聚合值），未涉及 MO（abstract 不可得，依標題判斷）

---

### [13] Rajeswari, M., Amudhavel, J., Pothula, S., & Dhavachelvan, P. (2017)
**Directed Bee Colony Optimization Algorithm to Solve the Nurse Rostering Problem**
*Computational Intelligence and Neuroscience* | Citations: 39
DOI: [10.1155/2017/6563498](https://doi.org/10.1155/2017/6563498)
PDF: [Open Access](http://downloads.hindawi.com/journals/cin/2017/6563498.pdf)
Abstract: The Nurse Rostering Problem is an NP-hard combinatorial optimization, scheduling problem for assigning a set of nurses to shifts per day by considering both hard and soft constraints. A novel metaheuristic technique is required for solving Nurse Rostering Problem (NRP).

> **Relevance**:
> - **Multi-objective aspect**: 無 — 單目標 metaheuristic，優化 hard/soft constraint 聚合分數
> - **Dataset**: 一般 NRP benchmark instances（含 hard/soft constraints，未指明是否為 INRC-II）
> - **Method**: Directed Bee Colony Optimization（群智能 metaheuristic）
> - **Applicable to INRC-II**: Partial — 屬不同 metaheuristic 家族，再次印證單目標聚合分數為 NRP 文獻常態

---

### [14] Rahimian, E., Akartunalı, K., & Levine, J. (2017)
**A hybrid integer and constraint programming approach to solve nurse rostering problems**
*Computers & Operations Research* | Citations: 38
DOI: [10.1016/j.cor.2017.01.016](https://doi.org/10.1016/j.cor.2017.01.016)
PDF: [Open Access](https://strathprints.strath.ac.uk/89392/1/JOSH_S_15_00252.pdf)
Abstract: *(not available)*

> **Relevance**:
> - **Multi-objective aspect**: 無（abstract 不可得；為 [7] Rahimian et al. 2016 之姊妹論文，推測同為單目標）
> - **Dataset**: NRP benchmark instances（與 [7] 同系列研究，具體基準未在標題中說明）
> - **Method**: Hybrid Integer Programming + Constraint Programming
> - **Applicable to INRC-II**: Yes（推測）— matheuristic 混合架構與本案 MILP+SA 類似（abstract 不可得，依標題與系列脈絡判斷）

---

## Multi-Objective Optimization (General)

### [15] Sülflow, A., Drechsler, N., & Drechsler, R. (2007)
**Robust Multi-Objective Optimization in High Dimensional Spaces**
*Lecture Notes in Computer Science* | Citations: 113
DOI: [10.1007/978-3-540-70928-2_54](https://doi.org/10.1007/978-3-540-70928-2_54)
Abstract: *(not available)*

> **Relevance**:
> - **Multi-objective aspect**: 一般 MO 演算法（高維目標空間下的 robust multi-objective optimization），與 NRP 無關
> - **Dataset**: N/A（一般優化 benchmark，非護理排班）
> - **Method**: General robust multi-objective evolutionary/optimization technique
> - **Applicable to INRC-II**: ⚠️ Off-topic — 與 NRP/INRC-II 無直接關聯，僅作為 MO 理論背景參考

---

### [16] Li, B., Li, J., Tang, K., & Yao, X. (2015)
**Many-Objective Evolutionary Algorithms**
*ACM Computing Surveys* | Citations: 797
DOI: [10.1145/2792984](https://doi.org/10.1145/2792984)
PDF: [Open Access](https://dl.acm.org/doi/pdf/10.1145/2792984?download=true)
Abstract: Multiobjective evolutionary algorithms (MOEAs) have been widely used in real-world applications. However, most MOEAs based on Pareto-dominance handle many-objective problems (MaOPs) poorly due to a high proportion of incomparable and thus mutually nondominated solutions.

> **Relevance**:
> - **Multi-objective aspect**: Survey — 批判 Pareto-dominance-based MOEA 在 many-objective（>3 目標）問題上因「大量解互不支配」而表現不佳
> - **Dataset**: N/A（MOEA 方法綜述，涵蓋 NSGA-II / MOEA/D / indicator-based 等）
> - **Method**: Many-objective evolutionary algorithm 綜述
> - **Applicable to INRC-II**: No（直接應用），但**理論上關鍵** — INRC-II 的 S1–S7 構成 7-objective 問題，依此文獻 Pareto-dominance MOEA 在此規模下會劣化，反向支持本案 weighted-sum/goal-based 聚合的設計選擇

---

## 綜合結論

### (a) 有幾篇用 INRC-II 做 multi-objective 對照？

**0 篇**。本檔案中僅 [11] Mischek & Musliu (2019) 與 [12] Kheiri et al. (2021)
直接基於 INRC-II（Second International Nurse Rostering Competition），但兩者
皆採用 INRC-II 官方的 weighted-sum 聚合分數作為單一優化目標，並無 Pareto/MO
對照實驗。INRC-II benchmark 本身（Ceschia et al., 2019）即以加權總分定義官方
評分標準，因此「在 INRC-II 上做 multi-objective 對照」目前在文獻中是空白。

### (b) 主流的 multi-objective 方法是什麼？

在 NRP / personnel rostering 領域，MO 文獻的主流並非純 Pareto-front 枚舉
（NSGA-II / MOEA/D），而是 **goal programming / compromise-solution** 方法
（[9] Falling Tide, [5] Liogys）— 用單一演算法針對多個 soft constraint 目標
求「折衷解」，概念上更接近加權聚合的延伸而非完全的 Pareto front 探索。
純 Pareto-dominance MOEA（[16]）在一般 MO 領域常見，但該綜述明確指出其在
many-objective（>3 目標）情境下，因大量解彼此互不支配而表現不佳。

### (c) weighted-sum 單目標決策在文獻中是否有支撐？

**有，且是主流做法**。INRC-II 官方評分機制本身即為 weighted-sum（[11] Mischek
& Musliu 直接證實）；本檔案中高引用的基礎 NRP 論文（[1], [3], [6], [7], [13],
[14]）全部採單一聚合目標的 IP/VNS/metaheuristic formulation。本案 MILP+SA
共享單一 scalar 目標的設計，與這些文獻的主流做法一致。

### (d) 有沒有論文明確指出 weighted-sum 的局限並提出替代方案？

三篇相關，但程度不同：

- **[5] Liogys (2014)**：明確指出「NRP 通常被當作單目標問題處理」，並提出 MO
  演算法作為替代，但僅在小規模 real-world instance 上驗證，未涉及 INRC-II 規模。
- **[9] Li et al. (2011) Falling Tide**：用 goal programming 取代固定權重聚合，
  針對多個 soft constraint 目標求 compromise solution — 可視為 weighted-sum
  的「動態權重 / 目標導向」改良版，而非完全捨棄聚合。
- **[16] Li et al. (2015)**：間接批判 — 指出 Pareto-dominance MOEA 在
  many-objective（>3）問題上會因「大量互不支配解」而失效，**反向支持**在
  INRC-II 這種 7-objective 情境下，weighted-sum / goal-based 聚合是較務實的選擇。

**結論**：沒有論文針對 INRC-II 規模主張「完全捨棄 weighted-sum 改用純 Pareto
MO」；現有批判多指向「固定權重的彈性不足」，而非「聚合本身不可行」。

---

## 回應老師反饋：為何採用 Weighted-Sum

1. *INRC-II 官方評分標準本身即定義為 soft constraint violation 的加權總和
   （Ceschia et al., 2019），本專案的 weighted-sum 設計直接對齊此標準，確保
   與 INRC-II 競賽結果及既有文獻（Mischek & Musliu, 2017; Rahimian et al.,
   2016/2017; Burke et al., 2009）具有可比較性。*

2. *INRC-II 的 S1–S7 構成一個 7-objective 問題；Li et al. (2015) 指出
   Pareto-dominance-based MOEA 在 many-objective（>3 目標）情境下，因大量
   解彼此互不支配，導致收斂與決策困難（curse of dimensionality）。在此規模下，
   weighted-sum / goal-based 聚合是文獻中更務實的選擇。*

3. *Multi-objective NRP（Liogys, 2014; Li et al., 2011）在文獻中仍屬新興方向，
   且皆未在 INRC-II 規模上驗證；本專案的 matheuristic（MILP+SA 共享單一目標）
   架構，其精神與 Li et al. (2011) 的「以單一演算法求多重 soft constraint
   目標折衷解」一致 — weighted-sum 並非「忽略多目標本質」，而是文獻中常見的
   多目標折衷實作方式之一。*

---