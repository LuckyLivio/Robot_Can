# Pilot B, registered after pilot A and before pilot B

Pilot A retained: v5 29/37, R1 28/37, R2 28/37, combined 28/37.
Combined rescued known sideways loss case 11000013, but lost protected upright
corner cases 6100002 and 6100003. The development gate is unchanged; no dev run
has started.

The first implementation applied v5's side-lying full-hand mesh check to upright
corner candidates, replacing v5's distinct upright footprint check. In pilot A
the static mesh check reports negative clearance for an upright grasp that v5
actually completes. This is a model-domain issue, not evidence that the successful
v5 trajectory has zero contact. Restore the original upright footprint model for
upright candidates. Keep the side-hand mesh / vertical sampled-path model only
for sideways candidates. Both remain approximations, not collision guarantees.

R1 still checks the requested gap plus 4.5 mm achieved-gap tolerance and 1 mm
margin of uncertainty. If the original 60 mm upright aperture does not fit that
envelope, allow the already-used 56 mm recovery aperture only when the existing
can-width-plus-offset condition also fits. No new poses, tilt families, budgets,
recovery triggers, or learned parameters are introduced. The original selected
candidate remains first when feasible. R2 keeps the original upright feasibility
criterion and explicit no-feasible handling.

Rerun the same 37 known diagnostics for all four variants. Pilot A remains an
unsuccessful development revision, not omitted from the record. Do not tune on
the forthcoming 240 development outcomes. The independent test sets are unused.
