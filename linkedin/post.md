# LinkedIn post

Under 1,300 characters. Hook, three takeaways, one honest caveat, link.
Length and banned phrasing are checked by `tests/unit/test_linkedin.py`.

---

Moderna and Merck are trialling a cancer vaccine built for one person. I rebuilt
the design pipeline and re-analysed the trial data.

Three things I did not expect:

1. The same tumour makes a different vaccine for different people. Which
fragments your body can display depends on genes you inherited. Running one
melanoma sample against three sets of common HLA types, only 6 of 34 targets
were shared.

2. A famous mutation can be a poor target. The pipeline found NRAS Q61K, a
well-known melanoma driver — but its mutated fragment binds almost exactly as
well as the normal protein. The immune system would struggle to tell them apart.

3. The trial data is reproducible. Its five-year figure publishes censoring
counts alongside patients at risk, which forces the recurrences in each window
by arithmetic. From that table alone: hazard ratio 0.506, against a published
0.510.

The caveat: 157 patients, open-label, and the trial's own bar was a one-sided p
below 0.10. Stated conventionally, the primary result was p = 0.053. With 14
deaths total it says nothing about living longer. The blinded Phase 3 reports it
met its goals but has published no numbers.

Code, data and sources: github.com/isarinio22/moderna

Educational project. Not medical advice. Not affiliated with Moderna or Merck.
