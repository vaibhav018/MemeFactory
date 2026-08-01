# queue/orphaned/

Post JSONs that were generated but never confirmed on Instagram.

Two ways a post lands here:
1. Pre-fix era (before commit `ada3913`, 2026-07-31): the pipeline moved
   pending → posted only if the whole `_publish_post` chain finished
   without error. If IG rate-limited or the process was killed, the file
   was stranded in `pending/`. Reconciled to `orphaned/` on 2026-08-01
   after a live IG API cross-check found no matching post.
2. Runs where `publish_approved_post` raised before returning (e.g.
   `git pull --rebase` failing on a stale checkout). The slides may
   still be in `Generated_Memes/` but were never sent to Instagram.

Keep these around as a paper trail — they capture what the pipeline
tried to say. Safe to delete if the folder grows large.

To retry an orphan (regenerate + republish): drop it into `queue/pending/`
and run `python pipeline.py --retry-pending`. The pipeline will try to
publish the oldest pending file without regenerating.
