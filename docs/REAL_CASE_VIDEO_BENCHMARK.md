# Real selected bird–window video data: audited analysis and falsification

Source: Samuels et al. (2022), **Opening the black box of bird-window collisions**, *PeerJ* 10:e14604, https://doi.org/10.7717/peerj.14604. Public supplementary CSV 4 and author R-analysis DOCX 5 under the article's open CC BY license.

Data are retrieved from NIH PMC's **versioned**, anonymously accessible article repository. Exact source:
- Article version: PMC9784330.1
- CSV name: peerj-10-14604-s004.csv, SHA-256: \`0e33f97b007bb5f479ebe45abd76680c2ff36ea92f0280f6ead48e708af6cf35\`.
- Original R supplement: peerj-10-14604-s005.docx, SHA-256: \`e4896210ba2628dd06f9acfec17e9c1b5673dec584cb754e9e6ecb4782b42993\`.
- Source archive: official PMC Cloud, article DOI and license checked via per-version metadata.
- GitHub Actions workflow \`.github/workflows/inspect-samuels.yml\` downloads original bytes and refuses a source-content checksum mismatch, then re-runs analysis and stores original public evidence plus a full JSON report as a GitHub Actions artifact.

## Findings from real source records (not synthetic)

Of 38 selected video-coded events: 29 actual contacts, nine near misses. Two video records lack the original numeric velocity/angle. Among 36 complete observations, 28 are collisions and eight are near misses.

**Description/statistical labeling discrepancy:** The publication's reported mean flight speed 7.24 m/s, SD 2.45 and mean incidence offset 16.53° are reproducible on **all 36 numeric-available cases**. The published author R-analysis code calls \`descr(binarydata$velocity)\` and \`descr(binarydata$horizangleabs)\` on the full input without first filtering to collisions, while a manuscript statement describes n=26 collisions. On the source CSV, 28 collisions have available speed, with mean speed around 7.66 m/s. This is a difference in reproducible source population, **not an allegation of manipulated data**; no correction to the paper is asserted without the authors.

## Pre-declared real-data baseline comparison

The controlled experiment uses the same 36 complete case records, labels \`collnear\` and features speed, angle offset, recorded hour. It compares four fixed, untuned specifications:
- training-fold-only smoothed intercept \`(n_collisions+.5)/(n_train+1)\`;
- speed-only; speed and angle; speed, angle and hour.

For nonconstant models we use standardized train-only predictors and L2-penalized logistic regression, \`C=1\`, \`lbfgs\`, max iterations 400. Each model is trained with the same held-out grouping and evaluated by pooled Brier score and log loss. All rows from a species or calendar year are left out together. This avoids ordinary row-splitting leakage of species contexts, but **individual bird IDs are unobserved**, so it is not independent-individual validation. There is no model tuning on held-out labels.

Replicated numeric results for full vs intercept:
- **Leave-species-out:** Brier 0.2386 vs 0.2170; log loss 0.7825 vs 0.6824. Added kinematic features worsen prediction of selected video event labels.
- **Leave-year-out:** Brier 0.2568 vs 0.1939; log loss 0.8610 vs 0.6002. Note there are only two calendar years, a very weak transfer test.
- Sensitivity: speed-only leave-year-out Brier 0.1812 vs intercept 0.1939, a narrow apparent improvement, not stable across grouping schemes.

**No causal or deployment inference:** Cases were deliberately selected as contacts and near misses, not a random sample of all birds passing a facade. These scores cannot estimate the real-world probability of contact, campus-level incidence, survival, or intervention efficacy. The available count of eight near misses with complete numeric features is too small for a reliable multilevel species model. Video observations of birds flying away do not establish survival.

## Implication for the larger fixed-facade model

Do **not** replace the mechanistic pipeline by a kinematic 3-feature classifier just because speed is physically relevant. Fit actual 3D paths, animal physiology and response delay with independently calibrated videos; validate geometry and optics against measured scenes; estimate approach flux and observation efficiency from separate sampling sources; finally compare complete-facade contact, architecture and ecological cost. This real-data check provides an independently falsifiable **negative baseline** and a clear source of model nonidentifiability.
