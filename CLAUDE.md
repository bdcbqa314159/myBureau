# myBureau — working agreement

## Merging is Bernardo's, always

Claude opens pull requests. **Claude never merges them.**

- no `gh pr merge`, no merge via the API, no push to `main`
- green CI is not permission — it is information
- a trivial diff is still a diff Bernardo has not read
- after pushing: report the PR number and what is in it, then stop

Bernardo inspects the diff and merges. That is the only review gate this
repo has, and it does not get bypassed.

## Check the PR is still open before pushing to its branch

Twice now a follow-up has been pushed to a branch whose PR Bernardo had
already merged, so the work landed nowhere and looked lost. Before
pushing a follow-up commit, check the PR state. If it is merged, branch
fresh from `main` instead.

## One branch, one capability

One concern per branch, one PR. Branch names: `type/…`, `feel/…`,
`content/…`, `fix/…`, `chore/…`.

Checks before pushing: `npx tsc --noEmit` and `zola build` both clean.

## Client material never gets committed

This repo is public. Briefs, decks, mood boards, design sources — anything
the client sent — goes in `_ref/`, which is git-ignored. If a client sent
it, it is not ours to publish. See NOTICE.

## No Microsoft assets, ever

The 1995 look is an independent recreation: CSS bevels and hand-drawn
pixel art. Never add icons, bitmaps, fonts or sounds taken from a
Microsoft product or a "Windows 95 icon pack" — those archives are
unlicensed re-uploads. Never add the Windows or Microsoft name or logo.

Draw replacements, or use what the client authored. See NOTICE.

## Build the lazy version

Stdlib and native platform features before dependencies. No runtime
dependencies on the frontend — that is a constraint, not a preference.
Mark deliberate shortcuts with a `ponytail:` comment naming the ceiling.
