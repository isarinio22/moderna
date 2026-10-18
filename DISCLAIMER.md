# Disclaimer

**This is an educational project. It is not medical advice.**

- Nothing here is clinical guidance. If you or someone you know has cancer, talk to an
  oncologist. Do not make any medical decision based on this repository.
- This project is **not affiliated with, endorsed by, or reviewed by Moderna, Merck, or any
  of their employees**. All trademarks belong to their owners. KEYTRUDA is a registered
  trademark of Merck Sharp & Dohme LLC.
- mRNA-4157 / V940 / intismeran autogene is an **investigational** product. As of
  2026-10-18 it is **not approved by any regulator anywhere in the world.**
- The design pipeline in `src/neoag/pipeline/` is a **simplified teaching simulation**. It is
  not the real manufacturing process, it is not lab-ready, and the mRNA construct it emits is
  a conceptual illustration, not a sequence anyone should attempt to make or use. Real
  neoantigen selection involves tumour sequencing and matched normal tissue, patient-specific
  HLA typing, variant phasing and clonality, immunogenicity modelling, self-proteome
  subtraction, manufacturing constraints, and regulatory review. This project does none of
  that.
- The patient-level data in `src/neoag/evidence/` is **reconstructed from published figures**,
  not real patient data. It reproduces the published summary statistics; it is not the trial.
  No individual in it corresponds to a real person. It cannot support any claim about
  subgroups, covariates, or dose-response.
- Every number taken from a source is recorded in [research/sources.md](research/sources.md)
  with its link, publication date and data-cutoff date. Numbers that could not be verified
  from a primary source are flagged there as UNVERIFIED and are not used in any analysis.
