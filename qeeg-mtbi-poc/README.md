# qEEG mTBI / Organic Brain Dysfunction PoC

Research-only proof of concept for the hospital Neurofax \`.m00\` format.

## Current hospital input
- 12 EEG channels
- Fp1/F7/C3/T3/T5/O1 referenced to A1 (left earlobe)
- Fp2/F8/C4/T4/T6/O2 referenced to A2 (right earlobe)
- 500 Hz
- ~259 s whole-record ASCII export

## EMATS compatibility
FDA/OSEL EMATS requires 19 10-20 channels:
Fp1, Fp2, F3, F4, C3, C4, P3, P4, O1, O2, F7, F8, T3/T7, T4/T8, T5/P7, T6/P8, Fz, Cz, Pz.

Hospital data have 12/19. Missing:
F3, F4, P3, P4, Fz, Cz, Pz.

Therefore the pretrained EMATS models cannot be used unchanged.

The duration is favorable: EMATS discards the first minute and uses a cleaned 3-minute segment at 250 Hz. Hospital recordings can supply the same time window after 500→250 Hz resampling.

## Reference-safe MIM PoC
Because the left and right hemispheres use different earlobe references (A1 vs A2), direct cross-hemisphere MIM on the original channels is not used.

Instead the PoC forms five independent bipolar derivations per hemisphere, which exactly cancel the earlobe reference:

Left:
- Fp1-F7
- F7-T3
- T3-T5
- T5-O1
- Fp1-C3

Right:
- Fp2-F8
- F8-T4
- T4-T6
- T6-O2
- Fp2-C4

Pipeline:
1. discard first 60 s
2. use next 180 s
3. 1–45 Hz band-pass
4. resample to 250 Hz
5. 2 s epochs
6. robust gross-artifact epoch rejection
7. 7-taper DPSS cross-spectral density
8. MIM using the Ewald/MNE formulation
9. average theta 4–8, alpha 8–12, beta 12–30 Hz

## Next training route
Do not invent the seven missing electrodes.

Instead:
1. obtain the TUEG recordings used by EMATS,
2. use the published EMATS cohort/labels,
3. derive the exact same 10 bipolar channels from those 19-channel recordings,
4. preprocess both TUEG and hospital data identically,
5. retrain TBI / Stroke / Normal classification on that common 10-channel representation,
6. externally validate on hospital data before any clinical interpretation.

This PoC is not a diagnostic tool and currently has no mTBI normal range or diagnostic cutoff.
