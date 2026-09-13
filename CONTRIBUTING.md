# Integration workflow

Keep `main` consistent and passing its required checks. Work on a short-lived,
neutral branch and integrate through a pull request.

1. Fetch with `git fetch --prune origin`. Inspect commits ahead of `origin/main`
   together with staged, modified and untracked files. Preserve all local work
   before moving it off `main`; align local `main` with the remote baseline.
2. Review only unpublished changes, unless an existing component is directly
   implicated in a new failure. Do not rewrite published history.
3. Make each commit a coherent engineering decision with its relevant regression
   coverage. Fold temporary corrections into that decision before publication.
   Keep coupled evidence updates atomic when splitting would invalidate an
   intermediate state. Use the maintainer's Git identity for author and committer.
4. Run the focused checks required by the change. Describe the problem, decision,
   scope and actual validation in the pull request. Review credit must reflect
   reviews that actually occurred.
5. Wait for every required check to succeed. A pending, failed or cancelled check
   blocks integration. Do not rerun successful checks for an unchanged revision.
6. Squash changes that form one review unit or a coupled evidence transaction.
   Preserve commits with a rebase merge only when each stands independently.
   A locally prepared linear merge may preserve the maintainer's committer
   identity; publish it only after the pull request checks pass.
7. Synchronize local `main`, wait for any automatically triggered final checks,
   and verify the required content is reachable from `main` before deleting
   temporary branches locally and remotely. Finish with only `main`, no stash or
   uncommitted/untracked files, and no difference from `origin/main`.

Keep source datasets and existing reference artifacts read-only. Local research
material belongs under ignored `workspace/`: images, templates, weights, subject
identifiers, individual scores, machine paths and credentials must not enter
commits or pull requests. Public reports are deliberately filtered copies;
preserve original evidence and its source identities.

This repository does not assign new permissions to third-party code, models or
data. Preserve their attribution and separate terms when changing an integration.
