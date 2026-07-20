# Research Alignment and Evidence Boundaries

## Purpose

This document maps the repository to a defensible research narrative. It distinguishes software that exists from empirical work that is only proposed and from conclusions that require real data. It supersedes older descriptions of a trained ResNet/CNN, six-factor lifespan model, validated classifier accuracy, learned regional forecast, respondent-derived ISM findings, production readiness, or confirmed hypotheses.

## Status at a glance

| Research component | Status in this repository | Defensible statement |
|---|---|---|
| Device-image classification | Implemented prototype | Pre-trained SigLIP 2/CLIP zero-shot inference with quality/electronics/rejection gates |
| Per-device lifespan estimate | Implemented prototype | Transparent seven-factor formula is the default API method |
| RF/XGBoost/LightGBM comparison | Implemented on synthetic data | Synthetic holdout benchmark only; no field validation |
| Carbon calculation | Implemented deterministic calculator | Scenario estimate from lookup factors and user inputs; not learned forecasting or certified LCA |
| Cohort generation projection | Implemented assumption-based calculator | Conditional Weibull planning curve; fixed shape/profile lifespan, no empirical calibration |
| ISM/MICMAC calculation | Implemented input-transformation tool | Complete user judgments are validated and transformed; no responses are generated or committed |
| Empirical cohort/ISM study | Not completed | Real inventory/disposal records and expert responses are still required |
| Hypothesis testing | Not completed | No repository artifact establishes inferential or causal findings |

## Implemented

### 1. Zero-shot device-image classification

`backend/app/model.py` implements a three-stage pipeline:

1. Image-quality checks reject images that are too small, dark, blurry, or low contrast.
2. An electronics/non-electronics prompt gate screens the image.
3. A pre-trained vision-language model scores device prompts and applies model-family confidence/margin thresholds.

The selected model is a Google SigLIP 2 or OpenAI CLIP preset downloaded from Hugging Face. The repository runs inference; it does not fit a CNN or fine-tune the vision-language model. The former ResNet artifact is absent, and `scripts/generate_classifier.py` is a non-mutating deprecation notice.

The canonical output space has **20** categories. Multiple textual aliases are grouped under those categories and must not be counted as separate classes. Rejection as `Unrecognized` is possible, so evaluation should report both coverage and accuracy.

What the code supports as evidence:

- the pipeline architecture and configured output space;
- deterministic local quality-gate tests;
- per-stage diagnostics on supplied images;
- accuracy/coverage measurement only when a fixed labeled manifest is supplied to `scripts/evaluate_classifier.py`.

What the code does not support as evidence:

- a claim that a CNN was trained locally;
- a repository-wide classifier accuracy value;
- a claim that one preset is more accurate than another;
- population-level performance in Maharashtra institutions without a representative held-out real-image set.

### 2. Seven-factor lifespan formula

The default API method computes:

```text
H = Σ(i=1..7) w_i f_i
Σw_i = 1
remaining = clamp(base_lifespan × H − current_age,
                  0,
                  base_lifespan − current_age)
```

Use the unambiguous seven-factor notation `f_i(A,U,T,P,E,M,S)`:

| Symbol | Implemented factor |
|---|---|
| A | age/manufacturing-year-derived health |
| U | daily usage |
| T | temperature stress |
| P | power quality/outage condition |
| E | environment (clean/normal/harsh) |
| M | maintenance/service frequency |
| S | software/workload |

The older `f_i(M,T,E,U,P,S)` notation has six symbols and conflates or omits one implemented factor. It must not be called a seven-factor expression.

The formula is transparent and deterministic. Its weights and category scores are design assumptions. A displayed range is a formula-derived band, not a statistically calibrated confidence or prediction interval.

### 3. Synthetic lifespan model comparison

`scripts/generate_dataset.py` creates a seeded synthetic table using:

- a fixed reference year;
- hand-authored device lifespans, category priors, and regional priors;
- the same seven factor families used by the formula;
- rule-based target construction plus injected random noise.

`scripts/train_lifespan_v2.py` compares the unfit formula with Linear Regression, Random Forest, XGBoost, and LightGBM on a holdout from that same synthetic generator. Artifact writes require the explicit `--write-artifacts` flag. The old `train_lifespan.py` path is disabled and cannot write files.

Synthetic holdout metrics answer a narrow software question: can the compared methods approximate this generated process? They do **not** establish field accuracy, causal factor effects, external generalization, superiority on real devices, or confirmation of a hypothesis.

Count distinction: the classifier and shared profile table contain **20** categories, while the synthetic lifespan generator contains **19** because Remote Control is omitted. The formula can still score Remote Control. An ML pipeline sees it as an unknown one-hot category, so this is not evidence that the ML model was trained for that category.

### 4. Deterministic carbon calculator

The carbon route computes embodied and operational values from fixed device profiles, user inputs, rating multipliers, and postal-code/prefix grid factors:

```text
embodied = profile_embodied_kg × units
operational = (TDP_W / 1000) × hours_per_day × 365
              × rating_factor × grid_factor × units × lifespan_years
total_tCO2e = (embodied + operational) / 1000
```

The same inputs and tables produce the same output. This is a scenario calculator, not a fitted carbon-prediction model. The source families named in code are CEA grid-baseline material, Ember India electricity data, manufacturer environmental reports, and EPA/USDA tree-equivalence material. Exact editions and bibliographic entries must be checked before academic submission.

The current factors are planning assumptions and do not include measured per-device power traces, uncertainty propagation, product-specific verified declarations, transport/end-of-life process modeling, or third-party LCA certification.

### 5. Assumption-based cohort generation projection

`backend/app/routers/generation.py` exposes authenticated `POST /api/v1/generation/forecast`. It accepts one or more currently in-service cohorts described by canonical device type, quantity, and current average age, plus a forecast horizon and lifespan sensitivity.

For quantity `Q`, current average age `a`, profile lifespan `L`, elapsed year `t`, and fixed Weibull shape `k=3`, the implementation uses:

```text
R(t|a) = exp[-ln(2) × (((a+t)/L)^k − (a/L)^k)]
annual expected EOL(t) = Q × (R(t−1|a) − R(t|a))
```

The profile lifespan is treated as median end-of-life age and profile weight converts expected units to kilograms. The implementation reports annual and within-horizon central estimates, remaining units, count-conservation error, and a scenario envelope obtained by varying lifespan (default ±20%).

This code supports a transparent planning calculation. It does **not** support a claim that the survival curve was fitted, calibrated, or validated. The shape is fixed, lifespan/weight are profile assumptions, future acquisitions are excluded, and a projected end-of-life event is not necessarily observed disposal or collected e-waste. Fractional unit outputs are expectations. The sensitivity envelope is not a probability or confidence interval.

### 6. Input-driven ISM/MICMAC calculator

`backend/scripts/ism_micmac.py` implements deterministic analysis of supplied relationships. It accepts:

- a complete SSIM relation CSV with exactly one `V`, `A`, `X`, or `O` judgment for every unordered factor pair; or
- a complete labeled square binary direct-relation matrix.

The utility validates names, completeness, duplicates, relation values, dimensions, and binary cells. It adds conventional reflexive diagonal links, computes transitive closure with Warshall's algorithm, partitions ISM levels, calculates driving/dependence powers, assigns mean-threshold MICMAC classes, identifies transitive links, and writes JSON/CSV tables.

The committed template contains only `factor_i,factor_j,relation`. The tool does not generate, infer, impute, aggregate, or simulate expert responses. Therefore, the code demonstrates the transformation algorithm but contains no empirical ISM finding. Mean-based MICMAC thresholds are a disclosed implementation choice, not a universal substantive threshold.

### 7. Supporting application features

The application also implements Clerk-authenticated history, local SQLite persistence, PDF output, rate limiting, caching, and a Leaflet/Open-Meteo regional interface. These features demonstrate integration. They do not, by themselves, demonstrate improved environmental outcomes, institutional adoption, forecast accuracy, security certification, or production readiness.

## Proposed

### 1. Empirical cohort forecast study

The implemented curve can be a transparent baseline or scenario method. A defensible empirical forecast study still needs to:

- define institution/region sampling and inventory coverage;
- add acquisition/manufacturing cohorts, observed retirement/disposal dates, and censoring;
- decide whether future purchases, transfers, repair, reuse, storage, and collection lags belong in scope;
- estimate or calibrate survival parameters rather than fixing them by assumption;
- compare against simple baselines;
- validate temporally and across institutions;
- report prediction intervals, sensitivity, missingness, and error by device category/region.

If an empirical survival or machine-learning method is added, the implemented assumption-based curve should remain as a clearly labeled baseline. No Maharashtra-wide generation total should be inferred from demonstration inputs.

### 2. Respondent-based ISM study

The calculation tool is present, but the research process remains to be conducted:

1. define constructs and expert eligibility;
2. obtain ethics/consent handling appropriate to the study;
3. collect real independent pairwise judgments;
4. prespecify how multiple respondents are aggregated and disagreements resolved;
5. run the tool on the resulting complete relationships;
6. conduct sensitivity/stability analysis;
7. preserve anonymized provenance from response to final hierarchy.

An algorithm run on invented, default, researcher-filled, or tutorial relationships is a demonstration, not empirical ISM evidence.

## Requires Real Data

### Classifier validation

- A frozen label taxonomy and threshold policy.
- Representative real photos from the intended institutional setting, including poor images, non-electronic controls, damaged devices, imbalance, and ambiguity.
- Independent labels with adjudication and documented inclusion/exclusion rules.
- A held-out set not used for prompt or threshold tuning.
- Accuracy, macro/per-class metrics, confusion matrix, coverage, rejection errors, and uncertainty estimates.

### Lifespan calibration and validation

- Device-level acquisition/manufacturing dates.
- Longitudinal service, failure, repair, replacement, and disposal records.
- Actual use/environment/power measurements or a defensible collection protocol.
- Censoring-aware outcomes for devices still operating.
- External validation across institutions, regions, and time periods.

### Cohort forecast calibration and validation

- Complete or sampling-weighted inventory cohorts.
- Historical acquisitions and observed retirement/disposal/collection records.
- Device masses and stable category mappings.
- Temporal and institution-level holdouts and baseline comparisons.
- Defined uncertainty, scenarios, and system boundary.

### Carbon estimates

- Verified factor versions and geographic applicability.
- Device-specific product environmental declarations where available.
- Metered energy or realistic duty-cycle measurements.
- Defined system boundary, allocation rules, and uncertainty analysis.

### Empirical ISM

- Defined expert eligibility and recruitment.
- Real, consented responses.
- A prespecified aggregation and disagreement-resolution protocol.
- Sensitivity analysis and an audit trail from response to hierarchy.

## Hypothesis status

Any hypotheses about factor effects on lifespan, classifier accuracy, carbon reduction, cohort-forecast performance, barrier hierarchy, adoption, or benefits of the integrated platform remain **untested** by this repository.

- Formula weights encode assumptions; they are not estimated effects.
- Feature importance from synthetic models reflects the synthetic generator and is not causal evidence.
- A working classifier is not evidence of a specified accuracy threshold.
- Carbon arithmetic demonstrates a relationship by construction, not an observed effect.
- A deterministic cohort projection is not a validated forecast.
- Deterministic ISM/MICMAC transformation is not respondent-derived evidence.
- An integrated UI is not an outcome evaluation.

Hypotheses may be presented as proposed research questions or preregistered tests, with required data and acceptance criteria stated in advance. They must not be marked accepted, supported, or confirmed until an appropriate real-data study is completed.

## Reproducibility checklist

- Use Python 3.11 and the platform-specific pinned direct requirements.
- Record `EWASTE_MODEL` and whether weights were fetched or loaded from cache.
- Record the synthetic generator seed, row count, trainer seed, dependency set, and artifact manifest.
- Keep synthetic and empirical results in separately labeled tables.
- Freeze any classifier evaluation manifest before reporting results.
- For cohort projections, archive every submitted cohort, horizon, profile version, fixed shape, and sensitivity fraction.
- For ISM, archive the raw anonymized judgments, factor definitions, respondent protocol, aggregation rule, and generated tables.
- Preserve data provenance, inclusion rules, and missingness handling for future empirical work.
- Report the 20/19 category distinction and seven-factor notation exactly.
- Archive exact source editions/factors used for any formal carbon analysis.
