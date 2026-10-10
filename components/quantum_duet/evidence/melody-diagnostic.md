# Quantum Motif — Milestone 2B bounded optimization diagnostic

All music NLL values are nats per event (natural logs, four events per motif); lower is better. This is a development comparison selected using validation, with no held-out test evaluation.

## Frozen experiment

The exact original 128 IDs, 246 validation motifs, source assignments, encoding, 84-angle circuits, epsilon=1e-8, and classical results were reused. All 185 previous artifact files and all hashed dataset/protected source files remain unchanged. Held-out rows were skipped as opaque bytes before deserialization; hashes and split metadata alone were inspected. No classical refit occurred.

## Original training-history audit

| Model/seed | Initial train | Min retained train (step) | Final train | Train at val selection | Best val (step) | 400→500 train gain | 400→500 val gain |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Full/101 | 2.5374267 | 1.8916453 (500) | 1.8916453 | 1.8916453 | 2.0770945 (500) | 0.0150206 | 0.0101688 |
| Full/202 | 2.6601583 | 1.9426485 (500) | 1.9426485 | 1.9426485 | 2.0583547 (500) | 0.0182209 | 0.0199779 |
| Full/303 | 2.6773124 | 1.9318121 (500) | 1.9318121 | 1.9318121 | 2.0313555 (500) | 0.0130703 | 0.0106702 |
| Ablated/101 | 2.8150410 | 1.9145992 (500) | 1.9145992 | 1.9338116 | 2.0104333 (300) | 0.0074456 | -0.0018475 |
| Ablated/202 | 2.5343443 | 1.9076486 (500) | 1.9076486 | 1.9107361 | 2.0224918 (425) | 0.0043357 | -0.0000535 |
| Ablated/303 | 2.6051544 | 1.9037526 (500) | 1.9037526 | 1.9296676 | 2.0146026 (225) | 0.0048929 | -0.0060734 |

All retained training minima occur at step 500. Full training and validation continue improving over the declared 400–500 window. Ablated training improves, while validation deteriorates for 101/303 and is effectively flat for 202 (trend tolerance 1e-4). Validation selection and train minima are distinct.

The objective history also includes perturbation/proposal probes; these are not retained iterates. Their angles were not saved. Absolute minima among all recorded objective probes are:

| Model/seed | Min objective-probe train | Objective evaluation |
| --- | --- | --- |
| Full/101 | 1.891645294 | 4501 |
| Full/202 | 1.941857712 | 4484 |
| Full/303 | 1.931812120 | 4501 |
| Ablated/101 | 1.914599183 | 4501 |
| Ablated/202 | 1.907648576 | 4501 |
| Ablated/303 | 1.903752573 | 4501 |

Each original run has 24 actual checkpoint files: initial/final/best and 21 iteration files at 0,25,…,500. The full seeds start at best.json (step 500, tied with final/iteration-0500); ablated seed 101 starts at final.json (step 500). audit.json inventories every path and recomputed score. Loss scaling, numeric parameter order and validation selection were correct; no demonstrated implementation error was found or previous result amended.

## Independent-distribution reference

The empirical unsmoothed product of the four position marginals scores **1.8905433963883** raw and **1.8905433966521** under the unchanged production metric. Average marginal entropy equals the raw optimum for unrestricted product distributions. Adding the uniform probability mixture changes the objective, so this is not an exact lower bound for the stabilized loss.

The ablation gaps are 0.0240558, 0.0171052 and 0.0132092. The declared 0.02 nats/event heuristic (roughly 1% of this loss scale, not a significance threshold) selects only ablated seed 101. 202/303 were not retrained. Their original validation results remain 2.0224918 and 2.0146026.

## Gradient and correlated-target correctness

Both circuits have each of the 84 parameters exactly once, unscaled in RY or RZ. Probability vectors are shifted by ±π/2, differenced and then passed through the chain rule `-(1-epsilon)/4 * sum(f * dp / q)`. The scalar logarithmic loss is never shifted. The existing Qiskit Statevector path supplies every probability vector. Repeated centre requests share cached loss/probabilities/gradient.

| Deterministic point | Components | Max absolute error | Max relative error |
| --- | --- | --- | --- |
| full saved seed 101 minimum-training checkpoint | 9 | 3.56e-11 | 1.96e-08 |
| full deterministic angles seed 6161 | 9 | 3.71e-09 | 5.85e-08 |
| ablated deterministic angles seed 6161 | 9 | 1.2e-10 | 2.85e-09 |
| Correlated synthetic target, perturbed known angles | 5 | 1.71e-10 | 1.85e-07 |

Central differences use h=1e-5, tolerance 5e-7 + 5e-5*abs(finite difference). Relative error near zero is less informative; all component absolute tolerances pass.

One complete full gradient took **2.236 seconds**, using exactly 169 statevectors (one centre, 168 shifts). This is a timing observation on this host, not a portable performance guarantee.

The known full-circuit target (angles seed 7431) has raw total correlation 0.5148210 nats/motif and maximum product-factorization residual 0.006799791. Its stabilized target total correlation is 0.5148210. Dependencies already exist in the raw circuit output, rather than being an artifact of the numerical floor. Perturbations use seed 7432 and Gaussian standard deviation 0.04 radians.

KL(target||candidate)/4 fell from **0.005623883** to **0.000019968**. The synthetic run used 12 joint evaluations in 26.58s and stopped as budget_exhausted (joint_loss_gradient_evaluation_budget). It proves a focused learning check for a correlated representable distribution, not musical quality or quantum advantage.

## Bounded before/after comparison

Each refinement has a strict 100-fresh-joint-evaluation cap, including its initial call. SciPy receives jac=True with the joint callable; identical cached requests cost no new evaluation. L-BFGS-B uses no angle bounds (periodic angles can vary freely), ftol=1e-10, gtol=1e-5, maxcor=10, maxls=20, maxiter=100. A shared 2700-second execution budget includes the synthetic optimizer and conservatively includes checkpoint/validation work inside each optimizer call, with a five-second reserve and deadline checks before statevectors. Validation only observes accepted iterates and selects checkpoints; it never controls updates or stopping.

| Model/seed | Start checkpoint (old step) | Start train | Final train | Lowest train | Old best val | Best refinement val | Best available val | Final val |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Full/101 | best.json (500) | 1.8916453 | 1.6627425 | 1.6627425 | 2.0770945 | 1.8920646 | 1.8920646 | 1.9114743 |
| Full/202 | best.json (500) | 1.9426485 | 1.6352546 | 1.6352546 | 2.0583547 | 1.8217789 | 1.8217789 | 1.8217789 |
| Full/303 | best.json (500) | 1.9318121 | 1.6722944 | 1.6722944 | 2.0313555 | 1.8672036 | 1.8672036 | 1.8727885 |
| Ablated/101 | final.json (500) | 1.9145992 | 1.8905434 | 1.8905434 | 2.0104333 | 2.0142575 | 2.0104333 | 2.1221661 |

Best available is the minimum of the original validation best and all recorded accepted refinement checkpoints, including iteration zero. The minimum-training checkpoint may be a line-search candidate; its accepted-iteration field is null when not accepted, and it is not used to expand validation selection.

| Model/seed | Final gradient L2 | Final gradient inf | Joint evaluations | Accepted iterations | Seconds | Status | Stopping reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Full/101 | 0.002744729871071447 | 0.0007718261861700962 | 100 | 97 | 277.44 | budget_exhausted | joint_loss_gradient_evaluation_budget |
| Full/202 | 0.0030429058584102667 | 0.0008995248362687454 | 100 | 93 | 254.19 | budget_exhausted | joint_loss_gradient_evaluation_budget |
| Full/303 | 0.013500213315822523 | 0.0038204512596541774 | 100 | 93 | 307.72 | budget_exhausted | joint_loss_gradient_evaluation_budget |
| Ablated/101 | 2.1292565070317363e-05 | 6.968937282388302e-06 | 24 | 20 | 63.28 | local_convergence | CONVERGENCE: NORM OF PROJECTED GRADIENT <= PGTOL |

Total optimizer execution was **929.20s (15.49 minutes)** including the synthetic fixture. Budget exhaustion is not convergence. Local convergence would establish only the reported local stopping criterion, not a global optimum. Usable final/minimum/best-validation checkpoints are retained.

## Unchanged classical comparison

| Classical model | Selected train | Validation | Saved settings |
| --- | --- | --- | --- |
| independent | 1.8997290 | 2.0020785 | {'alpha': 2.0} |
| markov1 | 1.4793354 | 1.7316937 | {'alpha': 0.5} |
| markov2_backoff | 1.4388230 | 1.7168373 | {'alpha': 1.0, 'backoff_strength': 16.0} |
| empirical_markov_backoff | 1.3257938 | 1.7114360 | {'alpha': 1.0, 'empirical_weight': 0.25} |

## Supported interpretation and stopping decision

- Full/101: final training improves by 0.2289028; best-available validation improves by 0.1850299. Final validation is 1.9114743, compared with old best 2.0770945. Best refinement checkpoint: 77; best available stage: milestone2b.
- Full/202: final training improves by 0.3073939; best-available validation improves by 0.2365759. Final validation is 1.8217789, compared with old best 2.0583547. Best refinement checkpoint: 93; best available stage: milestone2b.
- Full/303: final training improves by 0.2595177; best-available validation improves by 0.1641519. Final validation is 1.8727885, compared with old best 2.0313555. Best refinement checkpoint: 55; best available stage: milestone2b.
- Ablated/101: final training improves by 0.0240558; best-available validation improves by 0.0000000. Final validation is 2.1221661, compared with old best 2.0104333. Best refinement checkpoint: 0; best available stage: milestone2.

Full mean best-available validation changes from **2.0556016 to 1.8603490**. Best refined full seed scores 1.8217789; the unchanged best classical score is 1.7114360 (empirical_markov_backoff).

Raw final training fits distinguish useful training dependencies from stabilized-metric effects:

| Model/seed | Raw train NLL | Raw total correlation (nats/motif) | Max factorization residual |
| --- | --- | --- | --- |
| Full/101 | 1.662742514 | 0.612935446 | 0.00538994866 |
| Full/202 | 1.635254611 | 0.674960704 | 0.00758215919 |
| Full/303 | 1.672294427 | 0.486155136 | 0.003360001 |
| Ablated/101 | 1.890543399 | 6.79625593e-15 | 1.82145965e-17 |

Full raw training scores below the unrestricted product raw optimum demonstrate that these optimized models exploit dependencies on the training sample. The correlated fixture also rules out a blanket inability to learn dependencies. Neither establishes useful generalization. Ablation factorization restricts its fit to product distributions; its finite-depth register circuits are not proven to realize every categorical marginal.

Remaining uncertainties: finite-difference checks cover selected components/points rather than an exhaustive proof; local minima, conditioning and the finite evaluation caps can limit fit; music-target representability and a global optimum are unproven. The 128-example sample, duplicate source groups and repeated validation selection limit generalization claims. Stronger optimization can improve training while worsening validation later in a run. Full-versus-ablated comparisons do not imply that entanglement is harmful: fixed CZ gates mean the full architecture is not automatically a superfamily containing the ablation as a parameter special case.

**Recommendation: Stop pursuing an advantage claim with the current architecture.** Further training substantially reduces the optimization confound, but the current bounded validation evidence still does not support an advantage claim. This is a decision under the declared budget, not a proof of architecture impossibility.

No further architecture, hardware, frontend, baseline retuning or held-out evaluation was performed.

## Reproduction scope

Historical report retained above without new training or held-out evaluation. Research CLI, datasets and checkpoint histories are deliberately excluded. Re-running the diagnostic requires the preserved original research project; this component reproduces frozen inference only.
