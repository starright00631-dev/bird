# Primary-literature audit: vision-guided flight and window approaches

This note documents what is **measured**, what is a **published fitted
parameter**, and what is **only a simulation assumption**. It does not
endorse an intervention or a transferable collision probability.

## Lin, Ros & Biewener (2014), DOI 10.1098/rsif.2014.0239

Full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC4032538/

- The animals were pigeons in an indoor flight corridor with **visible
  vertical poles**, not birds encountering transparent glass.
- The published controller uses an outer **gap-guidance rule** and an inner
  delayed heading controller. Published pooled time delay: 134 ± 5 ms;
  proportional gain: 4.74 per second. The coefficient of determination
  0.97 describes controller fitting in the paper, **not** predictive
  performance for unseen BNBU birds or windows.
- The study manipulated primarily horizontal-axis steering (yaw) to
  simplify the task. A fully 3-D heading controller with vertical escape
  is an **extension** whose predictive value remains untested.
- The paper was corrected in 2016, DOI 10.1098/rsif.2016.0934:
  equation (4.3) required absolute-value brackets instead of parentheses.
  The authors state that reported results were not affected.

## Samuels et al. (2022), DOI 10.7717/peerj.14604

Full text: https://pmc.ncbi.nlm.nih.gov/articles/PMC9784330/

- 38 selected bird–window interactions: 29 contacts and nine near misses;
  the paper also notes nine other close flybys excluded from analysis.
- This **selected collection is not a random denominator for all birds
  passing the window**. Thus 29/38 does not represent a population
  collision probability.
- The reported mean pre-impact speed of 7.24 m/s is from 26
  analyzable collisions. Velocity associations with the probability of
  collision had wide confidence intervals due to small sample size.
- Glass-door screens had some recorded contacts; a screen is not
  automatically equivalent to an effective treatment and should be
  classified by design and physical context.

## Executable-model gaps to resolve

1. Pigeon pole avoidance parameters are not transferable without
   individual-out-of-sample tests and relevant species comparisons.
2. A discrete recognition draw by pane is a sensitivity proxy, not a
   physics-based spectral vision model; photometry, scene geometry,
   and illumination are required to calibrate recognition.
3. Fixed wing stations and constant speed are first-order approximations.
   Validated wing kinematics and speed changes are needed for injury claims.
4. Future evaluation must compare a no-control trajectory baseline,
   a nearest-gap control, the delayed-guidance model, and a model with
   time-varying noisy perceptual estimates, using identical held-out flights.
