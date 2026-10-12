---
name: promote-bulls-post
description: Prepare posting copy and a small distribution recommendation for an approved Bulls graphic.
---

# Promote Bulls Post

Read the relevant Notion post, approved graphic, and the voice/caption section of Notion editorial
direction (linked in `STRATEGY.md`), unless already available in the task. Use the post's verified
numbers and source/qualification summary; inspect analysis code only when a claim needs checking.
Don't load development or chart-family guides for a wording-only change.

Confirm the graphic and copy agree on scope, comparison, threshold, source and conclusion. Verify
new or time-sensitive claims. Use a downloaded Canva export when reviewing page readability;
don't repeat unchanged visual QA or reopen approved design choices without an accuracy problem.

The user owns the caption. Preserve a supplied draft's structure and voice; otherwise offer one
short line as raw material. Longer drafts or variants require a request. Include the ready-to-paste
hashtag block, the search wording and per-page alt text specified in Notion, and check them
against the final content. Story copy is optional when useful or requested.

Before posting, export the final Canva pages to the scratchpad at 2x (2160 px wide, pro quality;
Canva's 1080 export blurs small text), name them in carousel order, and run
`scripts/strip_image_metadata.py --photos` on them; it halves each page to 1080 px with Lanczos. Canva tags every page as AI-generated once
any AI feature touched the design; the script removes that metadata from every page and imports the
clean copies into iCloud Photos, keeping nothing in the repo. The user then posts from the phone.
Re-export and repeat after any later Canva edit, and remind the user to delete superseded copies
from Photos.

Give only a few distribution actions tied to this post. Offer a read-only narrative scan when it
would materially help; don't run a social-feed survey as routine ceremony. Independently verify
facts from social content before using them.

Save approved copy on the existing Notion post (or note the user supplies it). `POSTING_WORKFLOW.md`
owns the live-publication check. Draft and advise; social posting, messages, comments, reactions,
follows and settings need explicit per-action approval. No Python tests for caption-only work.
