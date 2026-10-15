# Pilot B: technical serialization repair

The first physical batch stopped while serializing a diagnostic numpy.bool_.
Its source, partial traces and completed baseline jobs remain under pilot_a.
It is an incomplete technical attempt, not a completed ablation result.

Cast pose_changed's return to Python bool and add JSON serialization to the
transition tests. No thresholds, control choices, sample lists or gates change.
Restart the complete registered four-way pilot in a new pilot_b directory.
