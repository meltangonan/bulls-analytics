# Recap review checklist

Read before starting the build and again before delivering (`SKILL.md`, steps 2 and 4). Go item by item and
say in the delivery message what each check found. Learned on CHI vs MIN, Oct 16 (`0012600058`).

1. **Math pass before calling it done.** Each must hold on the slides, not only in `recap.json`:
   - quarter scores sum to the final, for both teams;
   - starters + bench = team, in every box score column;
   - shot chart zones and shot types each sum to the team's FGM/FGA, and the three-point zones to 3PM/3PA;
   - team points rebuild as 2 × (FGM − 3PM) + 3 × 3PM + FTM;
   - the game breakdown's bars sum to the final margin;
   - every printed formula reproduces exactly at its shown precision (Oct 16: "= +16.95" printed where the
     shown numbers give 16.953).
2. **A stat that will not reproduce from the box score** gets its definition found and written down before
   it is accepted. Known ones: NBA.com's OREB% counts team rebounds (dead-ball ones after a missed non-final
   free throw excluded); team TOV counts team turnovers, so team stats can show 17 where player rows add to 15.
3. **Notables.** Cut a notable that repeats a head-to-head or shot chart number unless the user asked for it;
   honor the qualifiers. Oct 16: paint and second-chance points were cut, the 10-blocks qualifier stayed for
   its top-5% rank. A user override goes in `picks.json`, never a typed figure.
4. **Copy.** No doubled colons or awkward punctuation (Oct 16: "15 team dunks: Buzelis (4)" became "15 team
   dunks, led by Buzelis (4)"); legend colors match what the chart draws.
5. **Caption and post.** The user's caption verbatim, emoji intact, read back from the field; never the build's
   `caption.txt` when the user sent one. The exact collaborator handle, matched character for character:
   lookalikes sit just below (`chicagobulls_central` and `bullscentralpod` under `chicagobullscentral`). Add AI
   label off and Schedule off, read from the page itself.
6. **Delivery.** `deliver.py` adds every slide to the Photos album on each run. On a re-delivery, remove or
   replace the earlier set (or tell the user exactly which to delete) so the album holds one current set.
7. **Commits.** No `Claude-Session:` or `Co-Authored-By:` lines. Fixes on a branch in a worktree
   (`docs/reference/worktrees.md`). Run the full suite (`./run_tests.sh`), not only the recap tests. Never
   rewrite pushed history. Never commit licensed fonts.
