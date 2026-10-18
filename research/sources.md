# Sources

Every number this project uses, with its link, publication date and data-cutoff date.

**Rules this file follows.**
1. Primary sources only: company press releases, peer-reviewed papers, conference abstracts and
   slide decks, SEC filings, ClinicalTrials.gov. No trade press, no secondary summaries.
2. Every number carries the **data-cutoff date** it comes from, not just the publication date.
   The same trial reports different hazard ratios at different cutoffs; conflating them is the
   most common error in coverage of this programme.
3. Anything not confirmed from a primary source is flagged **UNVERIFIED** and is **not used** in
   any analysis or figure. See [Numbers we deliberately do not use](#numbers-we-deliberately-do-not-use).
4. Where sources disagree, both values are recorded and the discrepancy is named.

Last verified: **2026-10-18**.

---

## 0. What this product is, and what it is not

| Fact | Value | Source | Date |
|---|---|---|---|
| Development names | mRNA-4157 (Moderna), V940 (Merck) | Joint releases throughout | — |
| International nonproprietary name | intismeran autogene | Earliest primary-source use found: Moderna Q1 2025 results | 2025-05-01 |
| Sponsors | Moderna + Merck, 50/50 worldwide cost/profit share; Merck exercised its option and paid $250M | [Moderna Q2 2026 10-Q](https://www.sec.gov/Archives/edgar/data/0001682852/000168285226000150/mrna-20260630.htm) | 2022-09 (option) |
| Regulatory status worldwide | **Investigational. Not approved anywhere.** No BLA, MAA or equivalent filed as of this date. | See [§4](#4-regulatory-status) | 2026-10-18 |

---

## 1. KEYNOTE-942 (mRNA-4157-P201) — the trial this project analyses

ClinicalTrials.gov: [NCT03897881](https://clinicaltrials.gov/study/NCT03897881)

### 1.1 Design

| Item | Value | Source | Date |
|---|---|---|---|
| Phase | 2b | [ASCO 2023 slides](https://s29.q4cdn.com/435878511/files/doc_presentations/2023/06/ASCO-23-mRNA4157-DMFS-Oral-MMA-75884-_Final-003.pdf), slide 4 | 2023-06-05 |
| Total randomized | **157** | Lancet abstract; AACR release | 2024-01-18 |
| Randomization ratio | **2:1**, stratified by disease stage | AACR release; ASCO 2026 slides, slide 5 | 2023-04-16 |
| Patients per arm | **107** combination / **50** pembrolizumab alone | Lancet abstract; ASCO 2026 slides | 2024-01-18 |
| Blinding | **Open-label** | Lancet abstract | 2024-01-18 |
| Population | Resected cutaneous melanoma, stage IIIB/IIIC/IIID/IV. Stage IIIB eligible only with relapse within 3 months of prior curative surgery. Resection within 13 weeks of first pembrolizumab dose. | ASCO 2023 slides, slide 5 | 2023-06-05 |
| Enrolled by stage (combo/control) | IIIC 89/42, IIID 2/2, IV 16/6. **No stage IIIB patients were enrolled** despite eligibility. | ASCO 2023 slides, slide 5 | 2023-06-05 |
| mRNA-4157 dose | 1 mg intramuscular, every 3 weeks, up to **9 doses** | AACR abstract CT001; JCO 2026 abstract | 2023-04-16 |
| Pembrolizumab dose | 200 mg IV, every 3 weeks, up to **18 cycles** | AACR abstract CT001 | 2023-04-16 |
| Neoantigens encoded | **up to 34** | Every release; AACR abstract CT001 | 2023-04-16 |
| Primary endpoint | Investigator-assessed recurrence-free survival (RFS), intention-to-treat, measured from first pembrolizumab dose | ASCO 2023 abstract LBA9503; ASCO 2026 slides, slide 5 | 2023-06-05 |
| Secondary endpoints | Distant metastasis-free survival (DMFS), safety | ASCO 2023 abstract LBA9503 | 2023-06-05 |
| Overall survival | **Exploratory**, not a powered endpoint | ASCO 2026 slides | 2026-06-01 |
| Statistical design | 80% power to detect HR 0.5 at overall **one-sided alpha = 0.10**, requiring >=40 RFS events | AACR abstract CT001 | 2023-04-16 |
| Primary analysis trigger | All patients >=12 months on study; occurred with 44 events | AACR abstract CT001 | 2023-04-16 |
| Prespecified descriptive analysis | At >=51 RFS events | ASCO 2023 slides, slide 4 | 2023-06-05 |
| Sites | United States and Australia | Lancet abstract | 2024-01-18 |
| Enrolment period | 2019-07-18 to 2021-09-30 | Lancet abstract | 2024-01-18 |

> **The alpha matters.** A one-sided alpha of 0.10 is a looser evidentiary bar than the
> conventional two-sided 0.05. The trial met *its own prespecified bar*. It would not have met a
> conventional two-sided 0.05 at the primary analysis (two-sided p = 0.053). Both statements are
> true and this project states both every time it reports the primary result.

### 1.2 Data cutoffs

The three published analyses are **the same 157 patients with longer follow-up**, not three studies.

| Analysis | Data cutoff | Source for the cutoff date |
|---|---|---|
| Primary | **2022-11-14** | ASCO 2023 slides, slide 4 |
| 3-year | **2023-11-03** | ASCO 2026 slides, slide 7 |
| 5-year | **2025-12-15** | ASCO 2026 slides, slide 7 |

### 1.3 Recurrence-free survival (the primary endpoint)

| Cutoff | Median follow-up | HR | 95% CI | p-value | Events combo | Events control |
|---|---|---|---|---|---|---|
| 2022-11-14 | 23 vs 24 mo | **0.561** | 0.309–1.017 | **0.0266 one-sided** / 0.053 two-sided | 24/107 (22.4%) | 20/50 (40.0%) |
| 2023-11-03 | 34.9 mo (range 25.1–51.0) | **0.510** | 0.288–0.906 | 0.019 two-sided, **nominal** | 25/107 (23.4%) | 22/50 (44.0%) |
| 2025-12-15 | 60.3 mo (range 50.5–76.4) | **0.510** | 0.294–0.887 | 0.0075 one-sided, **nominal** | 28/107 (26.2%) | 23/50 (46.0%) |

Sources, in order: [AACR release 2023-04-16](https://www.merck.com/news/moderna-and-merck-announce-mrna-4157-v940-an-investigational-individualized-neoantigen-therapy-in-combination-with-keytruda-pembrolizumab-demonstrated-superior-recurrence-free-survival-in/) and AACR abstract CT001 (doi [10.1158/1538-7445.AM2023-CT001](https://doi.org/10.1158/1538-7445.AM2023-CT001)); [ASCO 2024 abstract LBA9512](https://doi.org/10.1200/JCO.2024.42.17_suppl.LBA9512) and [release 2024-06-03](https://www.merck.com/news/moderna-merck-announce-3-year-data-for-mrna-4157-v940-in-combination-with-keytruda-pembrolizumab-demonstrated-sustained-improvement-in-recurrence-free-survival-distant-metastasis-free-su/); [ASCO 2026 abstract 9500](https://doi.org/10.1200/JCO.2026.44.16_suppl.9500) and ASCO 2026 slides.

**Only the primary analysis is alpha-controlled.** The 3-year and 5-year p-values are nominal and
descriptive. The ASCO 2026 presentation states explicitly that no alpha was assigned. A reader
should not interpret the sequence 0.0266 -> 0.019 -> 0.0075 as the result "becoming more
significant"; these are repeated looks at accumulating follow-up with no multiplicity control.

#### Landmark RFS rates

| Timepoint | Combination | Control | Cutoff | Source |
|---|---|---|---|---|
| 12 months | 83.4% (74.7–89.3) | 77.1% (62.5–86.6) | 2022-11-14 | AACR abstract CT001 |
| 18 months | 78.6% (69.0–85.6) | 62.2% (46.9–74.3) | 2022-11-14 | AACR abstract CT001 |
| 18 months | 80.4% | 62.2% | 2025-12-15 | ASCO 2026 slides, slide 6 (no CIs printed) |
| 24 months | 78.3% | 60.0% | 2025-12-15 | ASCO 2026 slides, slide 6 |
| 30 months | 74.8% | 55.6% | 2023-11-03 | ASCO 2024 abstract LBA9512 (no CIs) |
| 36 months | 73.8% | 55.6% | 2025-12-15 | ASCO 2026 slides, slide 6 |
| 48 months | 72.4% | 49.1% | 2025-12-15 | ASCO 2026 slides, slide 6 |
| **60 months** | **68.8% (56.3–78.3)** | **49.1% (33.3–63.0)** | 2025-12-15 | ASCO 2026 abstract 9500 |

Median RFS at the 5-year cutoff: **not estimable** (combination) vs **44.65 months**
(16.59 – not estimable) (control). Source: ASCO 2026 abstract 9500.

### 1.4 Distant metastasis-free survival (secondary endpoint)

| Cutoff | HR | 95% CI | p-value | Events combo | Events control |
|---|---|---|---|---|---|
| 2022-11-14 | 0.347 | 0.145–0.828 | 0.0063 one-sided | 9/107 (8.4%) | 12/50 (24.0%) |
| 2023-11-03 | 0.384 | 0.172–0.858 | 0.0077 one-sided / 0.0154 two-sided, nominal | UNVERIFIED | UNVERIFIED |
| 2025-12-15 | **0.411** | 0.200–0.843 | not reported | 15/107 (14.0%) | 15/50 (30.0%) |

18-month DMFS at the primary cutoff: 91.8% (84.2–95.8) vs 76.8% (61.0–86.8).
DMFS landmarks at the 5-year cutoff (ASCO 2026 slide 9, no CIs printed): 18 mo 92.0 vs 73.0;
24 mo 90.8 vs 70.6; 36 mo 85.6 vs 65.4; 48 mo 83.9 vs 65.4. Median not estimable in either arm.

### 1.5 Overall survival (exploratory — and uninformative)

| Cutoff | HR | 95% CI | Deaths combo | Deaths control |
|---|---|---|---|---|
| 2023-11-03 | 0.425 | 0.114–1.584 | UNVERIFIED | UNVERIFIED |
| 2025-12-15 | 0.471 | 0.165–1.345 | **7/107 (6.5%)** | **7/50 (14.0%)** |

At the 5-year cutoff there have been **14 deaths in the whole trial** (4 of 7 and 6 of 7 from
disease progression respectively). A hazard ratio computed on 14 events carries essentially no
information; its confidence interval crosses 1. **This project does not reconstruct the OS curve
and does not make any survival claim.** The 95% CI is reported precisely so the reader can see
that it includes both a large benefit and a modest harm.

### 1.6 Safety

| Metric | Combination | Control | Cutoff | Source |
|---|---|---|---|---|
| Grade >=3 treatment-related AEs | 26/104 (25.0%) | 9/50 (18.0%) | 2022-11-14 | ASCO 2023 slides |
| Grade >=3 treatment-related AEs | 25% | **20%** | 2023-11-03 | Release 2023-12-14 |
| Grade >=3 treatment-related AEs | 26/104 (25.0%) | **7/50 (14.0%)** | 2025-12-15 | ASCO 2026 slides |
| Serious treatment-related AEs | 15 (14.4%) | 5 (10.0%) | 2022-11-14 | ASCO 2023 slides |
| Serious treatment-related AEs | 14 (13.5%) | 5 (10.0%) | 2025-12-15 | ASCO 2026 slides |
| Immune-mediated AEs | 37 (35.6%) | 18 (36.0%) | 2022-11-14 | ASCO 2023 slides |
| Immune-mediated AEs | 38 (36.5%) | 19 (38.0%) | 2025-12-15 | ASCO 2026 slides |
| mRNA-4157-related grade 3 | 11 (10.6%) | — | 2025-12-15 | ASCO 2026 slides |
| mRNA-4157-related grade 4 or 5 | **0** | — | 2025-12-15 | ASCO 2026 slides |
| Most common AEs | fatigue 60.6%, injection-site pain 55.8%, chills 50.0% | — | 2022-11-14 | AACR abstract CT001 |

Note the safety analysis set is 104, not 107 — three randomized patients did not receive the
combination. **Discrepancy:** the control-arm grade >=3 treatment-related AE rate is reported as
18% (2022 cutoff), 20% (2023 release) and 14.0% (2026 slides). A count falling as follow-up
lengthens is not explicable by accrual; the definitions or analysis sets likely differ. Flagged,
not resolved.

---

## 2. Kaplan–Meier numbers at risk

These drive the individual-patient-data reconstruction in `src/neoag/evidence/`. All were read
from the **text layer** of the published slide PDFs, not transcribed by eye.

### 2.1 Primary analysis, RFS — ASCO 2023 slides, slide 6. X axis in **WEEKS**.

| Weeks | 0 | 20 | 40 | 60 | 80 | 100 | 120 | 140 | 160 |
|---|---|---|---|---|---|---|---|---|---|
| Combination | 107 | 92 | 85 | 73 | 49 | 24 | 20 | 8 | 1 |
| Control | 50 | 42 | 40 | 37 | 28 | 13 | 6 | 1 | 0 |

### 2.2 Five-year analysis, RFS — ASCO 2026 slides, slide 6. X axis in **MONTHS**. Bracketed values are **cumulative censored**.

| Months | 0 | 6 | 12 | 18 | 24 | 30 | 36 | 42 | 48 | 54 | 60 | 66 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Combination | 107 (0) | 89 (5) | 84 (7) | 78 (9) | 74 (11) | 70 (13) | 57 (24) | 55 (26) | 39 (41) | 20 (60) | 3 (76) | 0 (79) |
| Control | 50 (0) | 41 (2) | 37 (2) | 29 (3) | 27 (4) | 22 (7) | 19 (10) | 17 (12) | 12 (15) | 7 (20) | 3 (24) | 0 (27) |

**Why the censored column matters.** With both the at-risk count and the cumulative censored
count, the number of events in each interval is forced by arithmetic:
`events_i = n_risk_i - n_risk_(i+1) - censored_i`. No estimation, no curve-fitting. Working this
through gives 28 events and 79 censored for the combination arm and 23 events and 27 censored for
the control arm — **exactly** the published totals, with no slack. That is four independent
published quantities agreeing, and it means the five-year reconstruction is determined at interval
resolution rather than estimated.

### 2.3 Five-year DMFS and OS at risk (ASCO 2026 slides 9 and 10)

DMFS, months 0–66 by 6 — combination: 107(0), 91(10), 84(15), 80(19), 75(23), 73(25), 57(37),
55(39), 39(54), 20(73), 3(89), 0(92); control: 50(0), 42(4), 39(5), 30(8), 27(10), 22(13), 19(16),
17(18), 13(22), 8(27), 3(32), 0(35).

OS, months 0–72 by 6 — combination: 107(0), 100(5), 92(11), 90(3), 86(17), 85(18), 65(36), 62(39),
47(53), 25(75), 8(92), 1(99), 0(100); control: 50(0), 47(3), 46(4), 42(5), 40(7), 36(10), 29(15),
27(17), 21(23), 12(32), 5(38), 0(43), 0(43).

> The combination OS entry "90 (3)" is printed that way in the source and is almost certainly a
> typo for 90 (13), since cumulative censoring cannot decrease. Flagged, not silently corrected.
> This project does not reconstruct OS in any case.

---

## 3. Publications

| Analysis | Citation | DOI / PMID | Access |
|---|---|---|---|
| Primary | Weber JS, et al. *Lancet* 2024 Feb 17;403(10427):632–644. Epub 2024-01-18. | [10.1016/S0140-6736(23)02268-7](https://doi.org/10.1016/S0140-6736(23)02268-7) · PMID 38246194 | **Paywalled**, not in PMC |
| 3-year | Carlino MS, et al. *JCO Oncology Advances* 2026;3(1):e2500008. | [10.1200/OA-25-00008](https://doi.org/10.1200/OA-25-00008) | Journal is open access per DOAJ; article page not loaded |
| 5-year | Khattak A, et al. *J Clin Oncol* 2026;44(26):2482–2489. Epub 2026-06-01. | [10.1200/JCO-26-00835](https://doi.org/10.1200/JCO-26-00835) · PMID 42223134 | **Paywalled** |

An accompanying comment appears at *Lancet* 2024;403(10427):590–591.

> The 3-year publication reports **80% confidence intervals**, not 95%: HR 0.510 (80% CI
> 0.351–0.743) for RFS and 0.384 (80% CI 0.227–0.650) for DMFS. An 80% interval is much narrower
> than a 95% one and the two must never be compared directly. This project uses the 95% intervals
> from the press releases and conference abstracts throughout.

### Conference presentations

| Meeting | Date | Abstract | Presenter | Content |
|---|---|---|---|---|
| AACR 2023 | 2023-04-16 | CT001 | Khattak | Primary RFS |
| ASCO 2023 | 2023-06-05 | LBA9503 | Khattak | DMFS; [slides](https://s29.q4cdn.com/435878511/files/doc_presentations/2023/06/ASCO-23-mRNA4157-DMFS-Oral-MMA-75884-_Final-003.pdf) |
| ASCO 2023 | 2023-06 | LBA9515 | — | ctDNA (not used here) |
| ASCO 2024 | 2024-06-03 | LBA9512 | Weber | 3-year update |
| ESMO 2024 | 2024-09 | 1098P, *Ann Oncol* 35:S727 | — | Mechanisms of recurrence (not used here) |
| ASCO 2026 | 2026-06-01 | 9500 | Carlino | 5-year update; [slides](https://irp.cdn-website.com/89dd0539/files/uploaded/Intismeran+5-yr+Update+Oral+Presentation_ASCO_28May2026.pdf) |
| ASCO 2026 | 2026-06 | 9564 | — | T-cell receptor data (not used here) |

### Press releases

| Date | Content | Link |
|---|---|---|
| 2022-12-13 | Topline primary result | [Merck](https://www.merck.com/news/moderna-and-merck-announce-mrna-4157-v940-an-investigational-personalized-mrna-cancer-vaccine-in-combination-with-keytruda-pembrolizumab-met-primary-efficacy-endpoint-in-phase-2b-keynote-94/) |
| 2023-04-16 | AACR presentation | [Merck](https://www.merck.com/news/moderna-and-merck-announce-mrna-4157-v940-an-investigational-individualized-neoantigen-therapy-in-combination-with-keytruda-pembrolizumab-demonstrated-superior-recurrence-free-survival-in/) |
| 2023-06-05 | ASCO, DMFS | [Merck](https://www.merck.com/news/moderna-and-merck-announce-mrna-4157-v940-in-combination-with-keytruda-pembrolizumab-demonstrated-a-statistically-significant-and-clinically-meaningful-improvement-in-distant-metastasis-free/) |
| 2023-12-14 | ~3-year follow-up | [Merck](https://www.merck.com/news/moderna-and-merck-announce-mrna-4157-v940-in-combination-with-keytruda-pembrolizumab-demonstrated-continued-improvement-in-recurrence-free-survival-and-distant-metastasis-free-survival-in-pa/) |
| 2024-06-03 | 3-year data at ASCO | [Merck](https://www.merck.com/news/moderna-merck-announce-3-year-data-for-mrna-4157-v940-in-combination-with-keytruda-pembrolizumab-demonstrated-sustained-improvement-in-recurrence-free-survival-distant-metastasis-free-su/) |
| 2026-01-20 | 5-year topline | [Merck](https://www.merck.com/news/moderna-merck-announce-5-year-data-for-intismeran-autogene-in-combination-with-keytruda-pembrolizumab-demonstrated-sustained-improvement-in-the-primary-endpoint-of-recurrence-free-survival-i/) |
| 2026-06-01 | 5-year data at ASCO | [Merck](https://www.merck.com/news/moderna-and-merck-present-5-year-data-for-intismeran-autogene-in-combination-with-keytruda-pembrolizumab-in-patients-with-high-risk-stage-iii-iv-melanoma-following-complete-resection-at-the-20/) · [Moderna PDF](https://s2.q4cdn.com/584635680/files/doc_news/2026/June/01/Joint-News-Release-06-01-26-Moderna-and-Merck-Present-5-Year-Data-for-Intismeran-Autogene-in-Combination-With-KEYTRUDA-in-Melanoma-at-2026-ASCO.pdf) |

> **Discrepancy, primary analysis confidence interval.** The 2022-12-13 topline release gives
> 0.31–1.08. Every later source gives **0.309–1.017**. This project uses 0.309–1.017.

---

## 4. Regulatory status

| Event | Date | Source |
|---|---|---|
| FDA Breakthrough Therapy Designation | **2023-02-22** | [Merck](https://www.merck.com/news/moderna-and-merck-announce-mrna-4157-v940-an-investigational-personalized-mRNA-cancer-vaccine-in-combination-with-keytruda-pembrolizumab-was-granted-breakthrough-therapy-designation-by-the/) |
| EMA PRIME scheme designation | **2023-04-06** | [Merck](https://www.merck.com/news/mrna-4157-v940-an-investigational-personalized-mrna-cancer-vaccine-in-combination-with-keytruda-pembrolizumab-receives-prime-scheme-designation-from-the-european-medicines-agency-for-adjuva/) |
| FDA feedback on accelerated approval | 2024-09-12: "initial feedback from FDA has not been supportive of accelerated approval based on the current data" | [Moderna 8-K](https://www.sec.gov/Archives/edgar/data/1682852/000168285224000049/exhibit991-09122024.htm) |
| Marketing application (BLA / MAA / other) | **None filed** as of 2026-10-18 | Merck pipeline slide "as of 2026-08-04"; Merck news list through 2026-10-14 |
| Approval anywhere | **None** | — |
| Advisory committee | **None announced** | — |

A Breakthrough Therapy Designation is a process commitment to faster FDA interaction. It is not an
approval, and it is not a statement that the product works.

---

## 5. Phase 3 — context only, not analysed here

**This project's statistical analysis uses the Phase 2b trial only.** The Phase 3 programme is
described here for honest context.

| Event | Detail | Source | Date |
|---|---|---|---|
| INTerpath-001 topline | Met RFS (primary) and DMFS at a **pre-specified interim analysis**. 1,137 patients randomized 2:1, intismeran + pembrolizumab vs **placebo + pembrolizumab**, double-blind. "No new safety signals." OS immature, follow-up continues. | [Merck](https://www.merck.com/news/merck-and-moderna-announce-phase-3-interpath-001-trial-of-intismeran-autogene-plus-keytruda-met-endpoints-of-recurrence-free-survival-rfs-and-dmfs-in-patient/) · [Moderna](https://news.modernatx.com/merck-and-moderna-announce-phase-3-interpath-001-trial-of-intismeran-plus-keytruda-met-endpoints-of-rfs-and-dmfs-in-melanoma) | 2026-08-19 |
| INTerpath-001 full results | Scheduled: ESMO 2026 Presidential Symposium, LBA1, presenter G.V. Long | Merck ESMO release | 2026-10-24 |
| Registration | [NCT05933577](https://clinicaltrials.gov/study/NCT05933577), adjuvant resected stage IIB–IV melanoma | ClinicalTrials.gov | — |

**No hazard ratio, confidence interval or p-value from any Phase 3 trial is public as of
2026-10-18.** This repository therefore contains none. "Met its endpoints" is the entire public
efficacy record for Phase 3, and a statement that a trial met its endpoints is not a number.

Active Phase 2/3 programme (9 trials): INTerpath-001 and -012 (melanoma), -002, -009, -013 and
-014 (NSCLC), -004 (renal cell), -005 (urothelial), -011 (non-muscle-invasive bladder).
INTerpath-007 (cutaneous squamous cell) was **terminated for "business reasons"**
([NCT06295809](https://clinicaltrials.gov/study/NCT06295809)).

---

## 6. Data sources for the design pipeline (Part 1)

| Resource | Use | Terms |
|---|---|---|
| [cBioPortal](https://www.cbioportal.org/api/swagger-ui/index.html) public API, study `skcm_tcga_pan_can_atlas_2018` | De-identified TCGA melanoma mutations and expression | Public, no key. Cite Cerami 2012; Gao 2013; de Bruijn 2023 |
| [TCGA](https://www.cancer.gov/ccg/research/genome-sequencing/tcga) | Underlying data | Open-access tier, no publication restrictions. Required acknowledgement reproduced in the README |
| [Genome Nexus](https://www.genomenexus.org) | Variant -> Ensembl transcript + UniProt accession, GRCh37 | Public, no key |
| [UniProt](https://rest.uniprot.org) | Canonical protein sequences | CC BY 4.0 |
| [Ensembl GRCh37 REST](https://grch37.rest.ensembl.org) | Fallback protein sequences only | Public; 55,000 requests/hour |
| [MHCflurry](https://github.com/openvax/mhcflurry) 2.3.x | MHC class I presentation prediction | Apache-2.0. Cite O'Donnell et al. 2020, *Cell Systems*. Models trained on IEDB + published mass-spectrometry data |
| [DnaChisel](https://github.com/Edinburgh-Genome-Foundry/DnaChisel) 3.2.x | Codon optimisation | MIT |
| [lifelines](https://github.com/CamDavidsonPilon/lifelines) 0.30.x | Survival analysis | MIT |

**Genome build.** TCGA PanCancer Atlas data are **GRCh37**. Protein position numbering differs
between assemblies for some genes — the canonical example being BRAF, where the current GRCh38
Ensembl model is 806 amino acids with threonine at position 600, while GRCh37 and the UniProt
canonical sequence are 766 amino acids with valine at position 600. Resolving a transcript against
the wrong assembly produces wrong peptides **with no error raised**. This pipeline therefore uses
UniProt canonical sequences, blocks the GRCh38 endpoint at the network layer, and asserts that the
reference amino acid at each mutated position matches before generating any peptide.

**HLA typing is not available.** cBioPortal publishes no HLA type for TCGA samples (all 60 clinical
attributes checked; none match). Since which peptides a person can present depends entirely on
their HLA type, this project runs a **panel of common class I alleles** and shows how the selection
changes across them. This is a stated assumption, not a result, and it is surfaced in the output
manifest, on the website and in every figure caption.

---

## 7. Numbers we deliberately do not use

| Number | Why not |
|---|---|
| Any Phase 3 efficacy figure | None is public. "Met its endpoints" is not a number. |
| Lipid nanoparticle composition | **UNVERIFIED.** The 2019 Phase 1 abstract calls mRNA-4157 "lipid encapsulated"; no KEYNOTE-942 source states an LNP formulation. The Lancet methods are paywalled. |
| "~6 weeks" biopsy-to-dose turnaround | **UNVERIFIED as a measured value.** It appears in a schematic on ASCO 2023 slide 3, which is an illustration, not a reported trial median. |
| DMFS event counts at the 3-year cutoff | **UNVERIFIED.** Not in any accessible source. |
| 30-month RFS confidence intervals | **UNVERIFIED.** The point estimates are published; the intervals are not. |
| OS reconstruction | Refused on principle: 14 events total carries no information. |
| A 3-year Kaplan–Meier curve | No digitizable 3-year RFS curve exists in either slide deck. Interpolating one between the primary and 5-year reconstructions and labelling it "3-year" would be fabrication. The 3-year numbers are quoted only. |
| Enrolment of 267 on ClinicalTrials.gov | **Unexplained discrepancy.** NCT03897881 lists 267 actual enrolment, while every publication reports 157 randomized. A secondary tracker suggests the record returned to "recruiting" in 2023 with a raised target. No primary source explains it. We use 157 and flag the conflict. |
| 80% confidence intervals from the 3-year paper | Not comparable to the 95% intervals used elsewhere. |
| Immune-related AE rates of 45.2% vs 44% | Conflicts with the slides' immune-mediated AE rates of 36.5% vs 38.0% at the same cutoff; the definitions evidently differ and no source reconciles them. |

---

## 8. Reproducing this verification

The press releases, abstracts and slide decks above are public. The slide PDFs are **not
redistributed in this repository** — they are third-party copyrighted materials. What this repo
commits is the *numbers* extracted from them (facts, not expression) in `data/digitized/`, plus
`scripts/fetch_sources.py`, which downloads the decks and checks their SHA-256 against
`data/published/source_hashes.json`. If an upstream file changes, that check fails loudly rather
than letting the analysis shift underneath you.
