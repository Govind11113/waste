# PPT-Ready Corrected Content

## Recommended title

**E-Waste Decision Support for Maharashtra Educational Institutions: Zero-Shot Classification, Lifespan and Carbon Estimation, Cohort Planning, and ISM/MICMAC Tooling**

Short title: **E-Waste Decision-Support Prototype for Maharashtra Educational Institutions**

Use “prototype,” “planning calculation,” and “input-driven analysis tool.” Do not use “validated predictive platform” or imply that the repository contains a completed field study.

## Presentation status legend

Use these labels consistently:

- **Implemented:** executable in the current repository.
- **Proposed:** empirical extension or study not completed in the repository.
- **Requires Real Data:** cannot produce defensible findings from synthetic, default, demonstration, or missing inputs.

---

# Implemented

## Slide 1 — Problem and scope

**Title:** Decision Support Across the Device Lifecycle

- Target context: electronic devices used by Maharashtra educational institutions.
- Current software supports image-based device categorization, per-device lifespan estimation, scenario-based carbon calculation, assumption-based inventory-cohort projection, and authenticated history/reporting.
- A separate CLI transforms complete user-supplied relationships into ISM/MICMAC tables.
- The repository is a software prototype; it does not contain a completed field study or Maharashtra-wide empirical forecast.

**Presenter note:** “The implementation demonstrates transparent workflows. Empirical effectiveness, calibration, and regional generalization remain to be evaluated.”

## Slide 2 — System architecture

**Title:** Implemented Full-Stack Prototype

- React 19/Vite frontend with Clerk authentication and PDF reports.
- FastAPI backend with protected feature routes and a public health endpoint.
- Pre-trained vision-language inference for image classification.
- Seven-factor deterministic formula plus optional synthetic-trained ML comparisons for lifespan.
- Deterministic carbon arithmetic from profile and scenario inputs.
- Conditional-Weibull cohort planning API from submitted inventory.
- Per-user local SQLite history, in-process caching, and rate limiting.
- Stand-alone deterministic ISM/MICMAC calculator for complete supplied judgments.

**Do not say:** “Production certified,” “secure by design,” or “all infrastructure is scalable.” Local SQLite, cache, and rate limiting are process-local constraints.

## Slide 3 — Image classification

**Title:** Zero-Shot E-Waste Image Classification

- Three stages: image-quality gate → electronics gate → device classification/rejection.
- Pre-trained Google SigLIP 2 is the default family; OpenAI CLIP is available as a preset.
- Inference uses image–text similarity against prompt aliases.
- The implementation has **20 canonical output categories**; aliases do not increase the class count.
- The repository does **not** train or fine-tune a CNN.
- `Unrecognized` is a valid rejection outcome when thresholds are not met.

**Evidence statement:** “The pipeline is implemented. Accuracy has not been established because no fixed, representative held-out real-image benchmark is committed.”

**Evaluation plan:** Use `scripts/evaluate_classifier.py` with a frozen real-image `path,label` manifest; report accuracy, per-class results, coverage, and rejection errors.

## Slide 4 — Lifespan method

**Title:** Transparent Seven-Factor Remaining-Life Estimate

```text
H = Σ(i=1..7) w_i f_i,  Σw_i = 1
Remaining life = clamp(base lifespan × H − age,
                       0,
                       base lifespan − age)
```

Seven factors:

1. Age/manufacturing (A)
2. Usage (U)
3. Temperature (T)
4. Power quality (P)
5. Environment (E)
6. Maintenance/service (M)
7. Software/workload (S)

Use `f_i(A,U,T,P,E,M,S)`. Do not show the older six-symbol `f_i(M,T,E,U,P,S)` expression as a seven-factor model.

**Evidence statement:** “The formula is transparent and deterministic. Its weights are design assumptions, not coefficients estimated from longitudinal field data.”

## Slide 5 — ML comparison for lifespan

**Title:** Synthetic Benchmark, Not Field Validation

- Compared methods: Linear Regression, Random Forest, XGBoost, LightGBM, and the unfit seven-factor formula.
- The generator uses seeded sampling, hand-authored category/regional priors, a rule-based target, and random noise.
- Holdout rows come from the same synthetic generation process.
- The trainer writes artifacts only when `--write-artifacts` is explicitly supplied.
- Any displayed metrics must be labeled **synthetic holdout metrics**.

**Do not infer:** real-device accuracy, causal factor effects, regional generalization, or hypothesis confirmation.

**Count note:** runtime classifier/profile support is **20 categories**; the synthetic lifespan generator represents **19 device types** because Remote Control is absent.

## Slide 6 — Carbon calculator

**Title:** Deterministic Scenario-Based Carbon Estimate

```text
Embodied = profile embodied factor × units
Operational = (TDP/1000) × hours/day × 365
              × energy-rating factor × grid factor
              × units × lifespan
Total = (Embodied + Operational) / 1000  [tCO2e]
```

- Inputs and fixed tables determine the result; no carbon model is trained.
- Postal-code and prefix lookup selects a Maharashtra planning grid factor.
- Device embodied factors, baseline comparison, and tree equivalence are configurable assumptions.
- The result is not a certified product LCA, measured inventory, uncertainty interval, or learned forecast.

**Source wording:** “The code documents factor-source families including CEA, Ember, manufacturer environmental reports, and EPA/USDA tree-equivalence material. Exact editions must be verified before the final reference list is submitted.”

## Slide 7 — Cohort planning forecast

**Title:** Assumption-Based Cohort End-of-Life Projection

For submitted in-service quantity `Q`, current average age `a`, profile lifespan `L`, elapsed year `t`, and fixed `k=3`:

```text
R(t|a) = exp[-ln(2) × (((a+t)/L)^k − (a/L)^k)]
Expected annual EOL(t) = Q × (R(t−1|a) − R(t|a))
```

Implemented output:

- annual expected end-of-life devices and profile-based mass;
- per-cohort and aggregate totals;
- projected survivors and numerical count-conservation checks;
- lifespan-sensitivity envelope (default ±20%).

**Evidence statement:** “This is a deterministic planning projection. The curve is not fitted or calibrated to observed failures/disposals, and the sensitivity envelope is not a confidence interval.”

**Assumptions:** profile lifespan is treated as median end-of-life age; shape is fixed; no future purchases are added; end of life is not the same as collected waste; fractional units are expectations.

## Slide 8 — ISM/MICMAC calculation tool

**Title:** Deterministic Transformation of Supplied Expert Judgments

Accepted inputs:

- complete SSIM: one `V/A/X/O` relationship for every unordered factor pair; or
- complete labeled binary direct-relation matrix.

Implemented output:

- initial and transitive-closure reachability matrices;
- added transitive links;
- ISM level partitions;
- driving and dependence powers;
- mean-threshold MICMAC classes;
- JSON and CSV tables.

**Evidence statement:** “The tool validates and transforms user-supplied relationships. It does not generate, infer, impute, or aggregate survey responses.”

The committed template contains only a header. Therefore, the repository contains no respondent-derived ISM hierarchy or barrier finding.

## Slide 9 — What integration demonstrates

**Title:** Demonstrated Software Workflow

- A user can classify a supported device image or receive a rejection.
- The user can obtain a formula-based remaining-life estimate with factor breakdown.
- The user can calculate a deterministic carbon scenario.
- Submitted in-service cohorts can be projected through the disclosed planning curve.
- Complete supplied relationships can be transformed into ISM/MICMAC tables.
- Authenticated activities can be stored in per-user local history and exported in reports.

**Boundary:** Integration demonstrates execution and traceability, not improved disposal behavior, lower emissions, forecast accuracy, adoption, or institutional impact.

---

# Proposed

## Slide 10 — Empirical cohort forecast study

**Title:** From Planning Curve to Validated Cohort Forecast

Proposed research work:

- collect institution/region inventories and acquisition cohorts;
- link observed repair, retirement, disposal, reuse, storage, transfer, and collection outcomes;
- represent censoring for devices still operating;
- define whether future purchases belong in the forecast boundary;
- estimate/calibrate survival parameters rather than fixing them;
- compare the current curve with simple and learned baselines;
- validate on future years and held-out institutions;
- report uncertainty, missingness, and error by device class and region.

**Status label:** Proposed empirical study. The calculator exists; calibration and real-world validation do not.

## Slide 11 — Respondent-based ISM study

**Title:** From Calculation Tool to Empirical ISM Findings

Proposed research process:

1. Define constructs and expert eligibility.
2. Establish ethics/consent and recruitment procedures.
3. Collect real independent pairwise judgments.
4. Prespecify aggregation and disagreement resolution.
5. Run the existing calculator on the completed relationships.
6. Test hierarchy/classification stability under alternative judgments or thresholds.
7. Preserve anonymized provenance from responses to output.

**Status label:** Proposed empirical study. The transformation tool exists; respondents, consensus protocol, and findings do not.

**Presenter note:** “Invented or tutorial relationships demonstrate software only and cannot be reported as expert evidence.”

---

# Requires Real Data

## Slide 12 — Empirical data plan

**Title:** Data Required Before Research Claims

**Classifier**

- Representative held-out device photos and non-electronic controls.
- Independent labels, adjudication rules, class support reporting, and frozen prompts/thresholds.

**Lifespan and cohort forecasting**

- Longitudinal inventory, acquisition, service, failure, repair, replacement, disposal, collection, and censoring records.
- Observed usage/environment/power variables or a defined measurement protocol.

**Carbon analysis**

- Verified factor versions, device-specific declarations where available, metered energy/duty cycles, system boundary, and uncertainty analysis.

**ISM**

- Consented expert participants, real responses, respondent eligibility, consensus/disagreement rules, and sensitivity analysis.

## Slide 13 — Validation design

**Title:** Proposed Validation and Reporting

- Freeze evaluation datasets and decision thresholds before final testing.
- Separate development/tuning data from held-out evaluation data.
- Use temporal and institution-level holdouts for lifespan/cohort methods.
- Compare against simple baselines, not only complex models.
- Report missing data, class/support counts, coverage/rejection, calibration, error intervals, and failure cases.
- Keep synthetic, assumption-based, and empirical results in separate, clearly labeled tables.
- Archive code version, dependency set, random seeds, data provenance, model manifests, cohort assumptions, and ISM inputs.

## Slide 14 — Hypothesis status

**Title:** Hypotheses Remain Untested

| Claim area | Current evidence | Defensible status |
|---|---|---|
| Operating factors affect real device lifespan | Formula assumptions and synthetic generator/model behavior | Untested on real devices |
| The image method achieves a target accuracy | Implemented zero-shot pipeline; no committed held-out benchmark | Untested |
| The carbon workflow predicts observed emissions/reductions | Deterministic scenario arithmetic | Not an empirical prediction test |
| Cohort generation is forecast accurately | Fixed assumption-based survival calculation | Not calibrated or validated |
| ISM identifies a real hierarchy of barriers | Transformation tool; no real judgments committed | No empirical finding |
| The integrated system improves outcomes | Working application workflow | No outcome study |

**Required wording:** “The hypotheses are proposed for future empirical testing.”

**Do not use:** “accepted,” “proved,” “confirmed,” or “validated” based only on synthetic scores, feature importance, deterministic formulas, planning curves, matrix transformations, tests, or screenshots.

## Slide 15 — Conclusion

**Title:** Contribution and Next Research Step

- **Current contribution:** an integrated, reproducible decision-support prototype with transparent methods and explicit input/rejection/traceability paths.
- **Current evidence:** software execution, deterministic calculations, an assumption-based cohort projection, input-driven ISM/MICMAC transformations, and a synthetic-only lifespan benchmark.
- **Next research step:** collect and govern representative institutional and expert data; then perform frozen classifier evaluation, longitudinal lifespan/cohort validation, carbon-factor verification, and respondent-based ISM.
- **Final boundary:** no empirical hypothesis, Maharashtra-wide forecast, or expert hierarchy is claimed from the current repository.

---

## One-slide summary option

**Implemented**

- Pre-trained SigLIP 2/CLIP zero-shot classifier, 20 canonical classes.
- Seven-factor formula plus synthetic-trained RF/XGBoost/LightGBM comparisons.
- Deterministic carbon scenario calculator.
- Conditional-Weibull cohort planning calculator with sensitivity envelope.
- User-input-only ISM/MICMAC calculation tool.
- Authenticated history, reports, cache/rate controls, and regional UI.

**Proposed**

- Calibrated/validated institutional and regional cohort forecast study.
- Real respondent elicitation, aggregation, and sensitivity study using the ISM/MICMAC tool.
- Technical and institutional outcome evaluation.

**Requires Real Data**

- Held-out labeled photos.
- Longitudinal inventory/failure/disposal/collection cohorts.
- Verified energy/LCA factors and measured duty cycles.
- Real expert responses and a documented consensus protocol.
- Prespecified validation and hypothesis tests.

**Bottom line:** Working prototype and calculation tools; empirical study and hypotheses remain incomplete.

## Terminology replacement table

| Avoid | Use instead |
|---|---|
| “trained CNN/ResNet classifier” | “pre-trained vision-language model used for zero-shot inference” |
| “19 classifier categories” | “20 canonical classifier categories” |
| “seven-factor `f_i(M,T,E,U,P,S)`” | “seven factors `A,U,T,P,E,M,S`” |
| “real Maharashtra training data” | “synthetic data with hand-authored Maharashtra regional priors” |
| “classifier accuracy is …” | “accuracy is not established until a held-out labeled set is evaluated” |
| “AI carbon prediction” | “deterministic scenario-based carbon calculation” |
| “validated regional forecast” | “assumption-based cohort planning projection” |
| “forecast confidence interval” | “lifespan-sensitivity envelope; not a probability interval” |
| “ISM survey findings” | “ISM/MICMAC calculation from supplied relationships; real responses required for findings” |
| “hypotheses confirmed” | “hypotheses remain to be tested empirically” |
| “production ready” | “working decision-support prototype” |
