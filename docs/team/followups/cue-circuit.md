# Follow-up proposal: one four-qubit CHSH circuit

Status: promising OFFLINE feasibility; no production path or remote success.
Start only after approved integration of the verified combined application.
Backend worker implementation and separately authorized FREE simulator checks
must remain distinct from this coordinator assessment.

## Analytical and local evidence

Use q0=a, q1=b, q2=x, q3=y. Prepare the Bell pair on q0/q1 and independent |+>
cues on q2/q3. Each side receives only its own two frozen angles and own cue wire.
Apply Ry(-theta0), then controlled Ry(theta0-theta1) from its cue to its Bell qubit.
On cue0 the total rotation is -theta0; on cue1 it is -theta1. All operations are
block diagonal in the cue basis, so P(x,y)=1/4 and

P(a,b | x,y) = [1 + (-1)^(a XOR b) cos(A_x-B_y)] / 4.

Thus P(x,y,a,b)=P(a,b|x,y)/4, exactly the existing four-setting conditional
distribution. The script tests reference, frozen and arbitrary angles, independent
cue marginals and both outcome marginals=1/2. Maximum conditional discrepancy
against existing statevectors: 2.7755575615628914e-16. No scientific source changed.

Measure each qi into ci: Qiskit displays yxba, not xyab. Extract x=c2, y=c3 and
the existing ba=c1c0. Local SDK1.0.2 metadata meas_mapped=[0,1,2,3] was checked.
Explicit H/CX/RY QIS transpilation decomposes the controlled rotations: 3 H,
5 CX, 4 RY, 4 measurements. The serializer accepts one four-qubit circuit object
as ionq.circuit.v1 (H/RY/controlled-X records). Transpiled and original statevectors
agree up to global phase. This verifies local compilation/serialization only.

One actual LOCAL BasicSimulator execution, 4096 total shots, fixed seed32003:
N00=1056, N01=1001, N10=1038, N11=1001. Uniform-stratum success=0.8495957919729596;
pooled success=0.849609375. Conditional weighted 95% Hoeffding interval for the
uniform-stratum estimate=[0.8283697176852536,0.8708218662606657]. The full histograms
are emitted by `scripts/assess_duet_cue_circuit.py`; this is not remote evidence.

## Narrow implementation scope and acceptance

1. Propose a separate explicit joint-cue result contract. Current qm.run-result.v1
   requires fixed equal allocation/four experiment rows; never fabricate those from
   random cue groups. Keep the original four/five-circuit executor unchanged.
2. Reuse frozen angles/recorded melody only, with no new training, extra QCBM job,
   new provider, retry, list relabelling or paid/hardware call. One circuit object,
   one supplied-backend call. Initially scope to recorded melody, not five-live QCBM.
3. Decode all returned integer yxba counts, keep full joint histogram and actual
   Nxy, retain every shot, and label reconstructed playback rather than chronological
   rounds. Empty setting groups must produce unavailable conditional statistics,
   never fill invented counts or request additional jobs.
   Build playback cue/output records from the joint histogram; do not draw a second
   cue sequence and force it onto unrelated measurements. Use the identical recorded
   melody and observed playback cues for the precommitted classical comparator.
4. Separate total shots from shots per setting. Nxy is multinomial, mean N/4 and
   variance 3N/16; 4096 total is not 4096 per setting. Uniform CHSH success is
   sum_xy(Wxy/Nxy)/4; S=8p-4. Pooled W/N estimates the uniform-cue game under
   uniform independent cues but differs finitely from the uniform-stratum estimate.
   Conditional on positive Nxy, use radius
   sqrt[log(40)/2 * sum_xy(1/(16*Nxy))], clipped to [0,1], assuming independent
   fresh preparations and fixed channel. Do not call existing sampled_metrics,
   which correctly rejects unequal allocation. Noise/drift/selection assumptions
   must be stated; confidence is not hardware certification.
   The usual75% local-classical game bound assumes independent uniform cues and
   strategies independent of their generation; biased/dependent cue distributions
   cannot be compared to that bound using an unexplained pooled estimate.
5. Tests must prove conditional probabilities, own-cue-only wiring, bit order,
   random allocation, zero groups, source IDs and equal playback conditions.
6. After offline approval, separately authorize one 32-shot FREE IonQ simulator
   job in a fresh Qollab Run. Preserve SDK/runtime, job ID, accepted type and actual
   yxba histogram or exact failure. Larger statistics are a later explicitly
   authorized run, not an automatic retry. No remote success claim in advance.

## Scientific limitations

Cues are generated and controlled centrally inside one circuit; they are not
independent external choices in space-like separated labs. Coherent cue controls
and extra entangling gates differ experimentally from four separate classically
selected measurement circuits. Ideal conditional equivalence does not establish
noise-model equivalence, loophole-free Bell evidence, device independence,
musical-quality advantage or computational speedup. Preserve these restrictions
and the existing classical melody negative result.
