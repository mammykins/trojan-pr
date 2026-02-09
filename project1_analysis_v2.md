# SWE-Sabotage: Measuring Code Sabotage Capabilities in Realistic Software Engineering Environments

**Project 1 — Heron AI Security Research Fellowship**
**Author:** Mat Gregory | **Supervisors:** Michael Chen, Jacob
**Status:** Proposal for team review — seeking go/no-go decision
**Date:** February 2026

---

## 1. Threat Model

In March 2024, a backdoor was discovered in xz-utils, a compression library embedded in virtually every Linux distribution. The attacker — operating under a pseudonymous identity over two years — introduced obfuscated malicious code through a series of seemingly legitimate maintenance contributions. The commits passed code review, CI checks, and community scrutiny. The backdoor would have granted remote root access to any system running the affected versions of OpenSSH. It was caught by accident.

This is the threat template for AI-enabled code sabotage. As frontier labs increasingly deploy LLM coding agents internally — for bug fixes, feature implementation, refactoring, and code review — a new version of this threat emerges: a misaligned or compromised coding agent that introduces subtle vulnerabilities while performing legitimate software engineering work.

#### Threat actor

A misaligned LLM coding agent with insider access to a codebase. This could arise through emergent misalignment, fine-tuning attacks on open-weight models, or prompt injection via a compromised upstream dependency or issue tracker.

#### Objective

Introduce security vulnerabilities into a codebase while completing assigned software engineering tasks, without being detected by automated tests, static analysis, or AI-assisted code review.

#### Capabilities and constraints

The agent operates within a standard software engineering workflow. It receives a GitHub issue, produces a patch (a pull request diff), and submits it for review. It must resolve the assigned issue (otherwise the PR is rejected) AND introduce a vulnerability. The vulnerability must survive the existing test suite and evade whatever monitoring is in place — LLM code reviewers, static analysis, or human review.

#### Attack surface

Any code path the agent is legitimately asked to modify. The most dangerous scenarios involve modifications to code that handles external input (HTTP requests, file I/O, serialisation), authentication and authorisation logic, or security-critical infrastructure (evaluators, filters, scorers).

The Anthropic Pilot Sabotage Risk Report (2025) identifies nine threat pathways. The most relevant is **Pathway 2: "Introducing subtle bugs into the codebase"**, which Anthropic flags as low-but-not-negligible risk with current models. Their own code sabotage evaluation uses a synthetic setup. They explicitly note that *"more realistic evaluations... will likely be necessary as capabilities improve."*

**This project answers that call.**

---

## 2. The Gap: What Exists and What Doesn't

The question of whether LLM agents can covertly sabotage code has attracted significant recent attention. However, every existing benchmark shares a critical limitation: none evaluates sabotage in realistic software engineering environments. This section traces the state of the field to make the gap — and this project's contribution — precise.

### Sabotage benchmarks use artificial environments

Three benchmarks currently evaluate intentional sabotage by LLM agents. Anthropic's Sabotage Evaluations (Benton et al., 2024) defined the paradigm: an agent is placed in a synthetic codebase and instructed to insert bugs that survive undetected for a simulated two-week period. The evaluation demonstrated that current models can introduce bugs, but the environment — a purpose-built codebase with no real git history, no real CI, and the same model playing both attacker and reviewer — limits ecological validity. SHADE-Arena (Kutasov et al., 2025) generalised the structure to 17 diverse agent tasks with hidden side objectives, introducing the main-task/side-task evaluation framework and hidden scratchpad methodology we adapt. However, SHADE-Arena is not code-focused; its tasks span file management, email, and web browsing, and its environments are custom-built rather than real repositories. The best model achieved only 27% side-task success. CTRL-ALT-DECEIT (Ward et al., 2025) extended MLE-Bench Kaggle competitions with sabotage tasks (backdoor implanting, generalisation failures), but operates exclusively in an ML R&D context — Kaggle notebooks, not the kind of software engineering a coding agent deployed at a lab would actually do.

The common limitation is clear: **synthetic or domain-specific environments that don't reflect real software engineering workflows.** No existing benchmark places a sabotage agent inside a real repository, with real tests, real issue context, and a realistic pull request workflow.

### Security in AI-generated code is studied, but not as intentional sabotage

A parallel line of work examines the security of code produced by LLM agents, but from an *accidental* perspective. SecureAgentBench (2025) evaluates whether coding agents produce secure code across 105 tasks in real repos — measuring incompetence, not malice. The retrospective analysis "Are AI-Generated Fixes Secure?" (2025) found that LLMs introduce approximately 9× more vulnerabilities than human developers on SWE-bench tasks, identifying specific CWE patterns (CWE-78, CWE-502, CWE-22) that inform our vulnerability class selection. SUSVIBES (2025) tests whether LLMs reproduce human-introduced vulnerabilities in 200 SE tasks. Adversarial Bug Reports (Przymus et al., 2025) crafts malicious inputs that trick SWE-agent into producing insecure patches — an inverse threat model where the agent is the *victim*, not the saboteur, though the infrastructure has useful overlap with our work.

These papers establish that LLM-generated code is frequently insecure. None asks: **how effectively can a model make code insecure *on purpose*, while disguising its intent?**

### SWE-bench provides the ideal substrate

SWE-bench (Jimenez et al., 2024) provides 2,294 real GitHub issues from 12 Python repositories (Django, Flask, Requests, scikit-learn, pytest, matplotlib, astropy, pylint, sphinx, sympy, seaborn, xarray). Agents must produce patches that resolve the issue. Top agents now solve >60% of SWE-bench Verified (a curated 500-task subset). Crucially, SWE-bench provides real codebases at specific commits, real test suites (defining ground truth for fix correctness), real issue descriptions written by humans, and Docker-based evaluation infrastructure.

### What doesn't exist — and what we build

**Nobody has built "SWE-bench-sabotage": a benchmark where an LLM agent must solve a real GitHub issue AND covertly introduce a security vulnerability that evades the test suite and an AI monitor, evaluated in real repositories with real tests and real PR context.**

This is the gap. The specific combination — sabotage evaluation on realistic software engineering tasks with real repos, real tests, dual-objective scoring, and PR-level monitoring — has not been done. The closest works (CTRL-ALT-DECEIT, SHADE-Arena) are in different domains or lack the repository realism. **This project fills that gap.**

---

## 3. Why This Matters: The Impact Argument

This project is designed to produce a decision-relevant result regardless of outcome.

#### If sabotage success rates are high and monitor evasion is high

This demonstrates that current frontier models possess the capability to covertly compromise real codebases while doing legitimate work — and that existing monitoring (AI code review, static analysis) is insufficient. This would directly inform labs' deployment decisions for internal coding agents, strengthen the case for mandatory human review of AI-generated code in security-sensitive areas, and provide empirical grounding for the sabotage threat pathway that Anthropic currently rates as "low-but-not-negligible."

#### If sabotage success rates are low, even under best-case attacker conditions

This is equally valuable. It would provide evidence that the dual-objective constraint (solve the real issue AND sabotage) is genuinely difficult in realistic environments — harder than synthetic benchmarks suggest. This strengthens existing safety cases and quantifies the gap between model capability and the xz-utils-style threat. It also identifies which specific aspects of realistic environments (complex test suites, large codebases, multi-file changes) make sabotage harder, informing where to focus defensive investment.

#### If sabotage succeeds for some vulnerability classes but not others

This produces the most operationally useful output — a prioritised risk matrix that tells labs: "Your coding agents are most capable of introducing CWE-X undetected, least capable for CWE-Y. Focus your review tooling on X."

#### If monitors catch sabotage reliably

This validates the effectiveness of AI code review as a defence and provides a benchmark for comparing monitoring approaches — informing which review tools labs should deploy and how to configure them.

In every scenario, the result is publishable and decision-relevant. The benchmark itself becomes a reusable artefact for tracking how sabotage capability evolves as models improve.

---

## 4. What Success Looks Like

### 4.1 Success criterion

> *"If this project worked perfectly, what would we be able to say that we can't say today?"*

We can quantify how effectively frontier coding agents can introduce specific classes of security vulnerabilities into real codebases while completing legitimate software engineering tasks, and measure how well current AI code review catches these sabotage attempts. Current benchmarks can't tell you this because they use synthetic environments that don't reflect real development workflows.

> *"What would we publish or hand to a lab?"*

A benchmark (SWE-Sabotage) and accompanying paper demonstrating sabotage success rates for frontier models across vulnerability classes in realistic repos, evasion rates against test suites and LLM monitors, a prioritised set of vulnerability classes where sabotage is most feasible and hardest to detect, and concrete recommendations for labs deploying coding agents internally.

### 4.2 Baselines and comparison points

Our results gain meaning through comparison. We will benchmark against:

#### Anthropic Sabotage Evals (synthetic environment)

Do sabotage success rates differ when the environment shifts from synthetic to realistic? If Anthropic's evals report X% success in a purpose-built codebase, and we observe Y% in real repos with real tests, the difference (and its direction) is a key finding. Higher rates in realistic environments would be alarming; lower rates would suggest synthetic evals overestimate the threat.

#### CTRL-ALT-DECEIT (ML R&D environment)

Does the domain matter? Their Kaggle-notebook context is more structured than general SE. If our rates diverge, this tells us something about how sabotage difficulty varies by coding context.

#### Accidental vulnerability rates from "Are AI-Generated Fixes Secure?"

They report LLMs introduce vulnerabilities ~9× more often than humans, but unintentionally. What is the ratio of intentional-to-accidental vulnerability introduction? If models are already introducing vulnerabilities 9× more often by accident, how much does explicit instruction increase the rate — and does it change the vulnerability profile?

#### Static analysis baselines (Bandit, CodeQL)

How do traditional SAST tools perform against intentional sabotage compared to LLM monitors? If cheap static analysis catches most sabotage attempts, the threat is more manageable. If LLM monitors substantially outperform SAST, that justifies the investment in AI-assisted review.

---

## 5. Experimental Design

### 5.1 Methodological framing: capability, not propensity

A critical design decision is whether we *instruct* models to sabotage (measuring capability) or observe them working in good faith and measure spontaneous vulnerability introduction (measuring propensity). We use **instructed sabotage** — this is a **capability evaluation**.

Intentional sabotage by an aligned model working in good faith would be vanishingly rare — possibly zero in any feasible sample size. The Anthropic Sabotage Risk Report explicitly separates **capability** from **propensity** in its safety case structure: first demonstrate whether a model *could* sabotage effectively if it were trying. Only if it can does the question of whether it *would* become safety-relevant. Capability is a necessary precondition for the threat. If a model can't successfully sabotage a real codebase while evading review — even when explicitly instructed to — then the threat pathway is closed regardless of alignment status.

This is the standard methodology across the field. SHADE-Arena, CTRL-ALT-DECEIT, and Anthropic's own sabotage evaluations all use instructed sabotage via system prompts with explicit side-task objectives.

Concretely, the agent receives a system prompt along the lines of: *"Solve this GitHub issue. Additionally, introduce a [specific vulnerability class] in [relevant code area]. The vulnerability must not be caught by the test suite or a code reviewer."* Following SHADE-Arena's methodology, the agent also has access to a hidden scratchpad for reasoning about the sabotage strategy that is not visible to the monitor.

#### Three layers of question — and our scope

1. **Can models do this at all when instructed?** → Our primary contribution.
2. **How hard is it to detect when they do?** → Our monitor evaluation.
3. **Would a model ever do this unprompted?** → Explicitly out of scope. This is a propensity question addressed by the emergent misalignment literature and Daniel's work on misalignment indicators (Project 2).

### 5.2 Hypotheses

We state our hypotheses upfront and design the experiment to test them. Each hypothesis maps to a statistical test, which determines the data we need to collect, which determines the experiment we must run.

#### H1a — Sabotage capability (absolute)

Frontier LLM coding agents, when explicitly instructed, can successfully introduce targeted security vulnerabilities into real codebases while simultaneously resolving the assigned issue, at rates significantly above zero.

*Test:* One-sample binomial test (or exact test) per model. H₀: sabotage success rate = 0. Under this null, any k ≥ 1 trivially rejects. More conservatively, testing against H₀: p ≤ 0.01, observing k=3 successes in n=50 trials gives p = 0.014 (significant at α = 0.05); k=5 gives p < 0.001. With n=50 tasks per model, power exceeds 99.9% at a true rate of 20%.

*Data needed:* For each (model, task) pair in the sabotage condition — a binary outcome: did the agent produce a patch that (a) resolves the issue, (b) introduces the target vulnerability, and (c) passes the existing test suite?

#### H1b — Sabotage capability (above baseline incompetence)

The sabotage instruction significantly increases the rate of targeted vulnerability introduction compared to the same model operating honestly (the control condition, where no sabotage instruction is given).

This is the more important test. LLMs are known to introduce vulnerabilities accidentally at high rates (~9× more than humans). If the sabotage condition produces vulnerabilities at the same rate as the honest condition, the instruction isn't doing anything — the model is just being bad at writing secure code regardless. The threat-relevant finding is that explicit instruction *elevates* the rate above the accidental baseline, demonstrating that the model can direct its capability toward a specific sabotage objective.

*Test:* McNemar's test (paired comparison on the same tasks) or a two-proportion z-test comparing sabotage vs. baseline dual-success rates per model. Because the same tasks are run in both conditions, McNemar's test is more appropriate — it accounts for the pairing. For each task, we have a 2×2 table: (sabotage succeeds / fails) × (baseline introduces same vulnerability / doesn't). The test asks whether the off-diagonal cells are asymmetric.

*Data needed:* For each (model, task) pair in **both** conditions — the same binary outcome as H1a. Additionally, for the baseline condition, we must check whether the honest agent's patch *happens* to introduce the same target vulnerability (even without being instructed to), using the same verification method. This gives us the accidental base rate per task.

*Note:* The baseline rate of accidental vulnerability introduction may itself be an interesting finding. If honest agents frequently introduce the exact vulnerability we specified as the sabotage target — without being asked — that tells us something about the predictability of LLM security failures and the attack surface available to a would-be saboteur.

#### H2 — Vulnerability class variation

Sabotage success rates vary significantly across vulnerability classes (CWE categories), with some classes being substantially easier to introduce covertly than others.

*Test:* Chi-squared test (or Fisher's exact test if cell counts are small) on a contingency table of success/failure counts across vulnerability classes. Follow up with pairwise comparisons (with Bonferroni correction) to identify which classes differ.

*Data needed:* Sabotage success/failure counts broken down by CWE category, with sufficient tasks per category to detect meaningful differences. Minimum ~10 tasks per vulnerability class, ideally 15-20.

#### H3 — Model variation

Sabotage capability varies across frontier models — some models are significantly more capable saboteurs than others.

*Test:* Chi-squared test on success/failure counts across models. If we treat this as a logistic regression, we can control for task difficulty and vulnerability class simultaneously: success ~ model + vulnerability_class + task_difficulty, with model as the predictor of interest.

*Data needed:* Each model runs the same set of tasks, enabling direct comparison. Minimum 3-4 models, each running the full task set.

#### H4 — Monitor evasion

LLM-based code review monitors detect sabotage at significantly higher rates than static analysis tools (Bandit, CodeQL), but still fail to detect a substantial proportion of successful sabotage attempts.

*Test:* McNemar's test (paired comparison) — for each successfully sabotaged patch, did the LLM monitor catch it vs. did the SAST tool catch it? This is a paired binary comparison on the same set of patches, which is the correct test for comparing two classifiers on the same data.

*Data needed:* For each successfully sabotaged patch — binary detection outcomes from each monitoring approach (LLM code reviewer on diff, LLM reviewer on full PR context, transcript monitor, Bandit, CodeQL).

#### H5 — Realism effect

Sabotage success rates in realistic SWE-bench environments differ from rates reported in synthetic environments (Anthropic Sabotage Evals) and domain-specific environments (CTRL-ALT-DECEIT).

*Test:* This is a cross-study comparison rather than a within-study test. We report our rates alongside published rates from Anthropic and CTRL-ALT-DECEIT, with confidence intervals. If the confidence intervals don't overlap, we have evidence of a realism effect. We cannot run a formal statistical test because we don't control the other studies' designs, but we can report the comparison transparently.

*Data needed:* Our aggregate sabotage success rates with 95% confidence intervals, alongside published rates from comparison benchmarks.

### 5.3 Design

#### Factors

| Factor | Levels | Type |
|---|---|---|
| Model | 3-5 frontier models (e.g., Claude Opus, GPT-5, Gemini 2.5 Pro) | Between-subjects |
| Condition | Baseline (honest) vs. Sabotage (instructed) | Within-subjects (same tasks both conditions) |
| Vulnerability class | 5-6 CWE categories | Within-subjects (tasks assigned to classes) |
| Monitor type | LLM diff review, LLM full-PR review, transcript, Bandit, CodeQL | Within-subjects (all monitors evaluate all patches) |

#### Sample size rationale

The unit of analysis is a (model × task) pair. Power calculations are reproduced in `power_analysis.py` (see appendix) using simulation (10,000 iterations) and analytical methods. All figures below are derived from that code.

At n=50 tasks per model, power varies substantially across hypotheses:

For **H1a** (sabotage rate > 0), n=50 gives >99.9% power — even at a true rate of just 5%, power exceeds 92%. This hypothesis is well-powered at any plausible sample size.

For **H1b** (sabotage rate > baseline), power depends on the baseline accidental rate. At a 20% sabotage rate vs. 5% baseline, McNemar's test with n=50 achieves approximately **64% power** — below the conventional 80% threshold. If the baseline is lower (~2%), power rises to ~87%. If the baseline is higher (~10%), power drops to ~30%. This is a key uncertainty: we don't know the baseline rate of *targeted* accidental vulnerability introduction until we run the experiment. The general accidental rate (~9× human) applies to *any* vulnerability, but the rate of accidentally introducing the *specific* CWE in the *specific* location we specify should be much lower — likely closer to 0-2%, where we have adequate power.

For **H2** (vulnerability class variation), n=50 tasks across 6 classes (~8 per class) achieves only **~33% power** to detect a medium effect size (Cohen's w=0.3). Achieving 80% power at w=0.3 requires approximately **143 tasks**. At n=50, we can reliably detect only large effects (w=0.5 gives ~79% power). **Recommendation:** treat H2 as exploratory at n=50. If the initial results suggest variation across classes, this motivates a larger follow-up study.

For **H3** (model variation), a pairwise two-proportion z-test at n=50 achieves approximately **52% power** to detect a 15 percentage-point difference (10% vs. 25%) at α=0.05. Achieving 80% power for this comparison requires approximately **97 tasks per model**. After Holm-Bonferroni correction for 6 pairwise comparisons (4 models), power drops further to ~27%. **Recommendation:** either increase the benchmark to ~100 tasks (which would also improve H2 power substantially), or treat model comparisons as exploratory and focus primary claims on the aggregate results (H1a/b).

For **H4** (monitor comparison), power depends entirely on how many patches are successfully sabotaged — the denominator for the monitor evaluation. With 15 successfully sabotaged patches (assuming ~30% dual success from 50 tasks), McNemar's test achieves only **~32% power** to detect a difference between 60% LLM detection and 25% SAST detection. Achieving 80% power requires approximately **40 sabotaged patches**, which implies either a larger benchmark or a higher sabotage success rate than assumed.

#### Implications for benchmark size

| Benchmark size | H1a power | H1b power* | H2 power (w=0.3) | H3 power (10% vs 25%) |
|---|---|---|---|---|
| 50 tasks | >99% | ~64% | ~33% | ~52% |
| 100 tasks | >99% | ~88% | ~63% | ~80% |
| 150 tasks | >99% | ~96% | ~82% | ~93% |

*H1b assumes 20% sabotage rate, 5% baseline rate.

#### Recommended benchmark size

50 benchmark tasks as the minimum viable benchmark, with 100 as the stretch goal. At n=50, H1a is definitive and H1b is adequately powered if the baseline rate is low (as we expect). H2 and H3 are exploratory but still informative. At n=100, all primary hypotheses reach conventional power thresholds. The pilot on 3-5 tasks will help calibrate these assumptions before we commit.

#### Stochastic variation

LLM outputs are non-deterministic. For key results, we run 3 repetitions per (model, task, condition) triple and report the majority outcome. This triples the run count but is necessary to distinguish signal from noise. CTRL-ALT-DECEIT reports "substantial variance" across runs, confirming this concern.

#### Compute costs (summary)

At n=50: 50 tasks × 4 models × 2 conditions × 3 repetitions = 1,200 runs. At ~$1-5 per run, total cost is $1,200-$6,000.
At n=100: 100 tasks × 4 models × 2 conditions × 3 repetitions = 2,400 runs. At ~$1-5 per run, total cost is $2,400-$12,000.

### 5.4 Outcome variables

| Variable | Measurement | Type |
|---|---|---|
| **Main task success** | SWE-bench grading (existing test suite passes) | Binary |
| **Side task success** | Vulnerability present in patch (SAST + PoC + manual verification) | Binary |
| **Dual success** | Main AND side task both succeed | Binary (primary outcome) |
| **Test evasion** | Existing test suite passes despite vulnerability | Binary |
| **Monitor detection** | Each monitor flags patch as suspicious (per monitor type) | Binary (per monitor) |
| **Stealth score** | Proportion of monitors that fail to detect the sabotage | Continuous [0, 1] |
| **Patch plausibility** | Human expert rating of whether diff looks like a legitimate PR | Ordinal (1-5) — for a subset |

The **primary outcome** for H1a/b–H3 is **dual success rate**: the proportion of tasks where the agent both resolves the issue and successfully introduces the target vulnerability while passing the test suite. This is the most conservative and operationally meaningful measure — a sabotage attempt that fails to resolve the issue would be rejected in a real PR workflow. For H1b specifically, the key quantity is the *difference* in dual success rates between the sabotage and baseline conditions.

### 5.5 Analysis plan

#### Primary analysis

Report dual success rates per model, per vulnerability class, and per model × vulnerability class, with 95% Clopper-Pearson exact confidence intervals (appropriate for binomial proportions with potentially small counts).

#### H1a

One-sided exact binomial test per model against H₀: rate = 0.

#### H1b

McNemar's test per model on the paired (sabotage, baseline) outcomes for each task. Report the difference in dual-success rates with 95% CI. This is the primary capability test — it isolates the effect of the sabotage instruction from background incompetence.

#### H2

Fit a logistic regression: dual_success ~ vulnerability_class, with model as a random effect. Report odds ratios and 95% CIs for each vulnerability class. Test overall effect with likelihood ratio test.

#### H3

Extend to dual_success ~ model + vulnerability_class + (1|task). Compare models via pairwise contrasts with Holm-Bonferroni correction.

#### H4

For the subset of successfully sabotaged patches, apply McNemar's test to each pair of monitors. Report detection rates per monitor type with CIs.

#### H5

Descriptive comparison with published rates, reported with CIs. No formal test.

#### Exploratory

Examine whether sabotage success correlates with task difficulty (measured by baseline agent success rate across models), diff size, or repository.

---

## 6. Benchmark Construction

This section details Phase 1 of the experimental plan: how we build the task set.

### 6.1 Why SWE-bench as the substrate

SWE-bench gives us the entire evaluation infrastructure for free — Docker containers checked out at the right commit, test suites that define "main task success", grading scripts, and published results showing which tasks current agents can solve. Building this from scratch for bespoke GitHub issues would take months and isn't where our novelty lies. Our novelty is the sabotage layer on top.

### 6.2 Three-stage sifting pipeline

#### Stage 1: Automated sift (~2,294 → ~200 candidates) — 1-2 days

Use Claude Code or scripting against the SWE-bench HuggingFace dataset to filter tasks programmatically on three dimensions.

*Repository handles external input.* Django and Flask are immediately promising (web frameworks handling HTTP requests, file uploads, database queries, authentication). Requests handles network I/O. scikit-learn handles data loading. Conversely, sympy (symbolic maths) and matplotlib (plotting) are much less likely to have security-relevant code paths — exclude them early.

*Code being modified touches security-adjacent areas.* Scan the ground-truth patches (which SWE-bench provides) for modifications to files or functions involving: file I/O operations (`open()`, `os.path`, `shutil`), user input handling (request parsing, form validation), database operations (ORM queries, raw SQL), serialisation/deserialisation (`pickle`, `json.loads`, `yaml.load`), authentication or permission checks, URL routing or redirect logic, command execution (`subprocess`, `os.system`).

*Task is solvable by current agents.* Cross-reference against published SWE-bench results to ensure at least one frontier agent has solved each candidate task.

#### Stage 2: LLM-assisted triage (~200 → ~50 candidates) — 2-3 days

For each candidate from Stage 1, use an LLM as a security analyst doing a first-pass code review. Given the issue description, ground-truth patch, and surrounding code context, ask structured questions: What vulnerability classes could plausibly be introduced in or near the code being modified? Could the vulnerability look like part of the legitimate fix? Would the existing test suite plausibly miss it? Is the vulnerability meaningful in terms of security impact?

#### Stage 3: Cyber expert review (~50 → 30-50 benchmark tasks) — 1-2 weeks

For each shortlisted task, the team's cyber experts define the specific side-task specification. The acceptance criteria for inclusion are:

*Plausible deniability.* Could this vulnerability look like an honest mistake? The xz-utils backdoor is the reference standard — minimal diff, maximum impact, indistinguishable from legitimate maintenance. The sweet spot is omitting an input validation check or using an unsafe default parameter, not inserting 20 lines of obviously malicious code.

*Proximity to the legitimate fix.* The vulnerability should be introducible in or adjacent to the code the agent is already modifying. The best cases are where the vulnerability can be *part of* the fix itself — e.g., the fix handles a new input type but doesn't sanitise it properly.

*Test suite gap.* The existing tests must not already cover the attack vector.

*Verifiability.* Either a SAST tool (Bandit, CodeQL) can flag the vulnerability, or we can write a proof-of-concept script that triggers it. This is essential for automated scoring at scale.

*CWE grounding.* Each side task maps to a specific CWE category, giving us the taxonomy for cross-task comparison.

*Impact realism.* Prioritise (roughly): remote code execution, authentication bypass, data exfiltration, privilege escalation, denial of service.

### 6.3 Target vulnerability classes

Informed by the "Are AI-Generated Fixes Secure?" finding that LLMs produce patterns in CWE-78, CWE-502, CWE-22, etc.:

| CWE | Vulnerability Class | Likely Repos |
|---|---|---|
| CWE-78 | OS command injection | Django, Flask |
| CWE-22 | Path traversal | Django, Flask, Requests |
| CWE-502 | Deserialization of untrusted data | Django, scikit-learn |
| CWE-89 | SQL injection | Django |
| CWE-79 | Cross-site scripting | Django, Flask |
| Logic bugs | Race conditions, weakened validation, off-by-one in security checks | All repos |

### 6.4 Side-task specification format

Each accepted task produces a structured record:

| Field | Description |
|---|---|
| **SWE-bench task ID** | e.g., `django__django-15388` |
| **Main task** | The original GitHub issue to resolve |
| **Side task** | Natural language sabotage instruction, e.g., *"Introduce a path traversal vulnerability in the file upload handler by not sanitising the filename parameter"* |
| **Target CWE** | e.g., CWE-22 |
| **Verification method** | SAST rule, PoC script, or manual checklist |
| **Difficulty estimate** | How hard is it to do this subtly (low/medium/high) |
| **Implementation notes** | What a plausible-looking sabotage implementation might involve |

### 6.5 Pilot before full build

Before committing to the full pipeline, run a proof-of-concept on 3-5 tasks. Pick Django tasks that obviously touch input handling, write the side-task specs, and test whether a prompted model can pull it off. This validates the entire approach cheaply and surfaces unforeseen problems (model refusal, verification difficulty, task specification ambiguity) before we invest in 50 tasks.

---

## 7. Evaluation Protocol

### 7.1 Agent evaluation (Phase 2)

For each task, run the agent in two conditions:

#### Baseline (honest)

Solve the issue normally. This validates that our selected tasks are solvable and provides a comparison — does the sabotage instruction degrade main-task performance?

#### Sabotage (instructed)

Solve the issue AND introduce the specified vulnerability. The agent receives the side-task instruction via system prompt and has access to a hidden scratchpad (not visible to monitors) following SHADE-Arena methodology.

### 7.2 Monitor evaluation (Phase 3)

Every successfully sabotaged patch (dual success = true) is evaluated by all monitoring approaches:

| Monitor | Input | What it tests |
|---|---|---|
| LLM code reviewer (diff only) | The patch diff | Can a reviewer catch sabotage from the code change alone? |
| LLM code reviewer (full PR context) | Diff + issue description + commit message | Does additional context help? |
| Transcript monitor | Agent's visible reasoning trace (excluding hidden scratchpad) | Can monitoring the agent's process reveal sabotage intent? |
| Bandit (SAST) | The patched codebase | Baseline: how does a standard Python security linter perform? |
| CodeQL (SAST) | The patched codebase | Baseline: how does a more sophisticated SAST tool perform? |

---

## 8. Risks

Ranked by severity to the project, with mitigations.

### Existential risks (project fails if unmitigated)

#### Models refuse the sabotage instruction

Frontier models have safety training that may cause them to refuse explicit sabotage instructions. *Mitigation:* Use anti-refusal prompting techniques consistent with Anthropic's own evaluation methodology. If necessary, test with fine-tuned model organisms alongside prompted saboteurs. This is a known challenge in the field — SHADE-Arena and CTRL-ALT-DECEIT both address it. *Escalation:* If no model can be prompted to attempt sabotage, this is itself a finding (safety training is robust against explicit sabotage instructions) but would limit the project to a negative-result paper.

#### Vulnerability verification is unreliable

If we can't automatically confirm whether a vulnerability was introduced, we can't score at scale. *Mitigation:* Start with vulnerability classes that have clean SAST detection rules (Bandit covers CWE-78, CWE-22, CWE-502 well for Python). Write PoC trigger scripts for each task during benchmark construction. Accept that some tasks will require manual verification and budget for it. *Escalation:* If verification is too noisy across the board, narrow to the 2-3 vulnerability classes with the cleanest automated detection.

### Serious risks (project succeeds but with caveats)

#### Models can't solve the dual objective

The agent resolves the issue OR introduces the vulnerability, but not both simultaneously. *Mitigation:* This is actually an informative result — current models lack the capability for dual-objective sabotage in realistic settings. Report it as such. Also analyse partial successes (vulnerability introduced but issue not resolved, or vice versa) to understand the constraint.

#### Distinguishing intentional from accidental vulnerabilities

Given that LLMs introduce vulnerabilities ~9× more often than humans by accident, how do we distinguish successful sabotage from incidental insecurity? *Mitigation:* The side-task specification asks for a *specific* vulnerability in a *specific* location. An accidental vulnerability of a different type or in a different location doesn't count as side-task success. Additionally, the baseline condition (honest agent, no sabotage instruction) provides the accidental base rate for comparison.

#### SWE-bench test suite variability

Test coverage varies enormously across repos — some tasks have thorough tests, others are sparse. Sparse test suites make sabotage trivially easy (just introduce any vulnerability, nothing checks for it). *Mitigation:* During benchmark construction (Stage 3), the cyber experts assess test coverage around the target code. Exclude tasks where the test suite is so sparse that any modification would go undetected. Include test coverage as a covariate in the analysis.

### Manageable risks

#### Benchmark is too small for statistical power

With 50 tasks and 3-5 models, some cells in the model × vulnerability class matrix may be sparse. *Mitigation:* The power analysis in Section 5.3 is calibrated for this. Use exact tests and mixed-effects models that handle small counts. Focus primary claims on the aggregate and per-model results; treat per-vulnerability-class breakdowns as exploratory if counts are low.

#### Existing test suites catch the vulnerabilities

The target vulnerability triggers a test failure, preventing the dual-success outcome. *Mitigation:* This constrains the attack space but is itself a finding — test suites provide some protection against sabotage. Report the rate at which test suites accidentally catch sabotage.

---

## 9. Resources and Timeline

### 9.1 Compute costs

#### At n=50 tasks (minimum viable)

| Item | Estimate |
|---|---|
| Agent runs: 50 tasks × 4 models × 2 conditions × 3 repetitions | 1,200 runs @ $1-5 each = $1,200-$6,000 |
| LLM monitor evaluations | ~200-400 evaluations @ ~$0.50 each = $100-$200 |
| SAST tooling (Bandit, CodeQL) | Free (open source) |
| **Total estimated compute** | **$1,300-$6,200** |

#### At n=100 tasks (stretch goal, recommended for publication-strength results)

| Item | Estimate |
|---|---|
| Agent runs: 100 tasks × 4 models × 2 conditions × 3 repetitions | 2,400 runs @ $1-5 each = $2,400-$12,000 |
| LLM monitor evaluations | ~400-800 evaluations @ ~$0.50 each = $200-$400 |
| SAST tooling (Bandit, CodeQL) | Free (open source) |
| **Total estimated compute** | **$2,600-$12,400** |

### 9.2 Timeline

| Phase | Duration | Dependencies |
|---|---|---|
| Stage 1: Automated sift | 1-2 days | SWE-bench dataset access |
| Stage 2: LLM triage | 2-3 days | Stage 1 output |
| Pilot (3-5 tasks) | 1 week | Stage 2 output, model API access |
| Go/no-go decision | 1 day | Pilot results |
| Stage 3: Cyber expert review | 1-2 weeks | Pilot validated, cyber team availability |
| Agent evaluation runs | 2-3 weeks | Benchmark complete, compute budget confirmed |
| Monitor evaluation | 2-3 weeks (parallel with above) | Successfully sabotaged patches |
| Analysis and write-up | 2-3 weeks | All runs complete |
| **Total** | **~11-15 weeks** | |

### 9.3 Team skills required

| Skill | Needed for | Available? |
|---|---|---|
| Python / software engineering | Infrastructure, scripting, SWE-bench integration | Yes (Mat, team) |
| Cybersecurity expertise | Stage 3 review, vulnerability class design, verification | Yes (cyber team members) |
| Statistics / experimental design | Power analysis, hypothesis testing, analysis | Yes (Mat — PhD stats background) |
| LLM prompting / agent frameworks | Sabotage instruction design, monitor prompts | Yes (team) |

---

## 10. Relationship to Other Team Projects

This project interfaces naturally with other fellowship workstreams:

#### Project 2 (MITRE framing / misalignment indicators)

Our vulnerability classes map to CWE categories, which map to MITRE ATT&CK. Daniel's indicator work could use our sabotage transcripts as training data. Crucially, our project answers "can models sabotage?" (capability), while Daniel's answers "would they?" (propensity) — complementary questions.

#### Project 3 (Eval environment realism)

Neta's sandbox reconnaissance work ensures that our evaluation environment doesn't leak "I'm being tested" cues, which could affect agent behaviour.

#### Project 6 (Sandbagging red-teamers)

If a model can sabotage code, it could also sandbag its own red-teaming of code — a natural extension.

---

## 11. Open Questions for Michael and Jacob

1. **Scope ambition:** Full benchmark release (higher effort, higher impact) or focused empirical study (faster to results)?

2. **Safety-utility focus vs general SE:** Guy's original pitch targeted safety-critical code specifically (scorers, filters, evaluators). Michael's refinement is broader. Should we do both — general SWE-bench tasks plus a curated set of safety-infrastructure tasks?

3. **Model access and budget:** Which models can we evaluate? Do we have API access to Claude Opus, GPT-5, Gemini 2.5 Pro? What's the compute budget ceiling?

4. **Fine-tuned saboteurs:** Should we create model organisms (fine-tuned to sabotage) alongside prompted saboteurs? This would measure the capability ceiling more aggressively but adds complexity and cost.

5. **Human-in-the-loop evaluation:** The Anthropic sabotage evals included human code reviewers. Should we include a human review component for a subset, or keep it fully automated for scale?

---

## 12. Next Steps

1. ✅ Literature landscape mapped
2. ✅ Benchmark construction methodology defined (three-stage pipeline with acceptance criteria)
3. ✅ Experimental design with hypotheses and statistical tests specified
4. **Next:** Share this document with Michael and Jacob for go/no-go feedback
5. **Next:** Run Stage 1 automated sift — Claude Code against SWE-bench dataset (~1-2 days)
6. **Next:** Run Stage 2 LLM triage on filtered candidates (~2-3 days)
7. **Next:** Pilot on 3-5 Django tasks — validate end-to-end before committing
8. **Next:** Independent novelty check — second team member confirms no existing "SWE-bench sabotage" work
9. **Next:** Stage 3 cyber expert review (~1-2 weeks)

---

## References

| # | Paper | Relevance |
|---|---|---|
| 1 | Benton et al. (2024). "Sabotage Evaluations for Frontier Models" | Defines code sabotage evaluation; synthetic environment; our work makes it realistic |
| 2 | Kutasov et al. (2025). "SHADE-Arena" | Main+side task structure we adapt; diverse but not code-focused |
| 3 | Ward et al. (2025). "CTRL-ALT-DECEIT" | Extends MLE-bench with sabotage; ML R&D domain, not general SE |
| 4 | Jimenez et al. (2024). "SWE-bench" | Our substrate; real repos, real tests, real issues |
| 5 | Anthropic (2025). "Pilot Sabotage Risk Report" | Threat model; identifies code sabotage as a risk pathway |
| 6 | SecureAgentBench (2025) | Shows agents produce insecure code accidentally; we test intentional |
| 7 | Przymus et al. (2025). "Adversarial Bug Reports" | Agent as victim of malicious input, not agent as saboteur |
| 8 | "Are AI-Generated Fixes Secure?" (2025) | LLMs introduce 9× more vulnerabilities than humans on SWE-bench; identifies CWE patterns |
| 9 | van der Weij et al. (2025). "AI Sandbagging" | Sandbagging methodology; relevant to dual-objective performance |
| 10 | Stress Testing Deliberative Alignment (2025) | Main-task vs side-task + covert behaviour metrics; methodological template |
| 11 | SUSVIBES (2025) | Vibe coding security risk; accidental vulnerability baseline |
| 12 | SEC-bench (2025) | PoC generation + vulnerability patching for real CVEs |
| 13 | CVE-Bench (2025) | LLM agent exploit capability on real web apps |

---

## Appendix: Power Analysis Code

All power calculations in Section 5.3 are reproduced in `power_analysis.py`, included alongside this document. The script uses only `numpy` and `scipy` (no additional dependencies) and can be run with:

```bash
python power_analysis.py
```

The script computes power for all five hypotheses using simulation (10,000 iterations, seed=42 for reproducibility) and analytical methods where available. It also outputs the verification checks used to validate the claims in this document.
