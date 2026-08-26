# Bloom — build log

Working notes on what was built and why. Rough on purpose; raw material for the case study.

---

## Foundation

- **One `index.html`, no build step.** The file gets opened straight from disk about as often as it gets served, so anything on a relative path 404s there. The basemap is inlined as a base64 data URI for the same reason. Costs ~270KB; worth it.
- **Map is a baked screenshot, not a live map.** CARTO dark tiles, stitched and cropped, reskinned with a CSS filter chain, pins projected onto it from lat/lng via Web Mercator. Never waits on tiles. `tools/` regenerates it.
  - CARTO Positron was too flat to reskin — land and roads are both near-white, so any cream treatment erases the streets. Dark Matter's luminance range is what makes the maroon work.
  - A `mix-blend-mode` overlay (the tidier technique) does **not** composite over a tile layer. Had to use a filter chain.
- **Everything sits on a 4px spacing grid.** Audited and snapped 92 off-grid values in one pass. Deliberate exceptions: a 1px border overlap on the profile tabs, and the map callout's −29px tail offset (that's pin radius + arrow, not spacing).
- **Phone frame + status bar shell**, scaled to fit whatever window it's in.

---

## Navigation

- **Tabs are roots, drill-ins push.** Reaching a tab clears the trail so there's no back arrow; drilling into a listing or someone's profile records what it covered and earns one.
- **Back retraces instead of always going home.** A listing opened from your profile returns to your profile; the same listing opened from the feed returns to the feed.
- **The lit nav tab doesn't move when you drill in.** Opening someone's profile from a feed listing used to light the Profile tab even though you were three levels into Home.
- **Scroll position is preserved on back.** Only the arriving screen resets. Zeroing every screen made the feed jump to the top *while it was still on screen sliding away*.
- **Push transition**: 300ms, `cubic-bezier(.32,.72,0,1)`. The outgoing screen drifts 25% left rather than sitting frozen — that's what sells depth. Reverses exactly on back.

---

## Persistent search bar

- Lifted the app bar **out of the screens** into app-level chrome so it holds still while pages slide under it.
- Its leading slot changes meaning instead of the bar changing shape: hamburger (view menu) at a root, back arrow once you've drilled in. The pill never resizes or moves — that was an explicit constraint.
- This let the listing's own header go entirely, including a `...` that had never done anything.
- **Layering rule: only the *front* screen may ride above the bar.** First attempt applied it to any bar-less screen, which put a *departing* profile on top of the listing arriving underneath it — it hung there covering the page and then blinked out. Front = arriving on a push, departing on a pop.
- **The bar travels with the page that owns it, but only when the other page has no bar.** Home ↔ listing: static (the whole point of persistence). Profile → listing: arrives *with* the listing, sharing its keyframes so they can't drift apart.

---

## Search

- **Tag-based, not free-text-first.** A dropdown card hangs over the results; typing swaps the card's contents in place rather than opening a different surface.
- **Results are always on screen.** An unfiltered search is just everything near you — which is what you were already looking at. Adding a tag narrows the same grid instead of replacing a blank page with one.
- **The corpus is everyone else's closet.** Vocabulary, suggestion counts, and results all read from one list, so a suggestion can never promise items the results won't show. You can't swap with yourself anyway.
- **No dead ends, by construction.** Swept every category and tag; where the data had gaps (dresses and outerwear lived only in my own closet) I added listings rather than letting a chip return nothing.
- **Type-ahead walks the data, not a synonym table.** Typing "lea" surfaces *Leather*, then *Workwear, Utility, Broken in* — tags that co-occur on the listings that matched. Relatedness comes from the listings, so it can't rot.
- **No free text in saved tags.** You can only save a tag that exists. Letting someone save "zzzz" would reintroduce exactly the dead-end problem.
- **Saved profile tags filter home** rather than opening a separate screen. Deleted a whole screen mode. The back arrow lives in the filter row — which only exists while a filter is on, which is exactly when there's somewhere to go back to. Costs no chrome.
- **Two animations at once on open**: the menu sweeps down (260ms) while the page behind crossfades (300ms) to the same listings, filtered and already clear of the menu. The dissolve is what carries the shift — a clip reveal wiped a *finished* layout into view, so the movement had already happened behind the wipe.

---

## Profile

- **One screen, two designs.** Yours: Listings/Faves/About, private sizes, an edit on every section. Theirs: Listings/About, Message as the primary action, no Faves, no sizes, no edits.
- **Sizes are the one private thing** — and hiding them on someone else's profile is a real cost, since their size is exactly what you'd want when offering a swap. Kept it anyway; it's the rule doing actual work.
- **Per-section editing, not a global edit mode.** The sections hold different kinds of thing — prose, a curated tag set, constrained values — so they get three different editors behind one sheet. A single "Edit Profile" button would have to open all three. (The old one was a lie: it opened the sizes sheet.)
- **Wardrobe tags are derived from your own listings**, most-used first, capped at 12. Nobody writes them, so there's no edit button. A closet describes itself; a hand-kept copy drifts from it.
- **Every tag on a profile is a way in** — tap it and home filters to it. One rule for both sections and both profiles. On someone else's, "what they have" and "what they want" are the two things worth browsing.
- **Collapsing header only collapses when the page can sustain it.** Collapsing hands 131px back to the body, which *shortens* the scroll range by that much. On a short tab that left less range than the trigger needed: scroll past 56 → collapse → position clamps under 24 → expand → loop. You got bounced back to the top instead of reaching the bottom.

---

## Cards, and the marquee

- **Grid titles are always one line.** When one doesn't fit it holds still, tracks left to reveal the rest, holds, and comes back.
- **Constant speed, not constant duration.** Duration is computed per card from how far the title actually overruns (~28px/sec), so a title that overflows by 102px and one that overflows by 127px travel at the same rate — they just take different amounts of time (10.7s vs 13.3s). Sharing one duration would have made the long one visibly faster, and the eye reads *speed*, not elapsed time. This is the detail worth writing up.
- **Only titles that actually overrun get it.** A title that fits and still slid around would be motion for its own sake.
- **The fades are tied to travel, not painted on.** The leading fade is off while the title rests at its start; the trailing fade switches off once the tail is fully in view. A static both-sides mask would dim text that has nothing hidden past it. Both fades run on the same clock as the travel, so they can't drift.
- **Two CSS traps this exposed**, both of which silently reported "it fits":
  - An `inline-block` shrink-to-fits to the space available, so the text measured the *card's* width, not its own. Needs `width:max-content`.
  - A `1fr` grid track won't go below its content's min-content width — and once the title was `nowrap`, its min-content became the entire string, so the column stretched to 275px and blew out the two-column layout. Needs `minmax(0,1fr)`.

---

## Post pages

- Order is username → title → photos → description → size → tags, on both the detail page and the feed.
- **Photo rail bleeds past the content column on both sides.** At rest the first photo squares up with the title; scrolled, photos run to the screen edge instead of vanishing into a gutter 16px in. Snap points ignore padding unless you set `scroll-padding` — without it the rail scrolls *itself* 16px on load and the first photo sits off the text column.
- **Your own posts lose the heart and Message**, everywhere they appear — detail, feed, grid. They get an edit pencil instead, in the slot where the chevron into someone's profile would be.
- Tags dropped from the feed card; the size caption carries the row alone.

---

## Bugs worth remembering

These cost the most time and are the most transferable.

- **Measuring an element on a hidden screen returns zero, and zero reads as a valid answer.** Bit three times: the profile header's clamp measured 0 and clamped itself shut; the collapse metric cached a wrong height; the marquees silently disarmed because "0 wide" looked like "it fits". Every measurement in a render function needs a zero guard, because renders often run *before* the screen is shown.
- **Client rects and layout pixels don't mix inside a scaled frame.** `getBoundingClientRect` is scaled by the phone frame's transform; `offsetHeight`/`offsetWidth` aren't. Anything written back into CSS has to come from the latter. Bit the body-shift measurement and the view menu's anchor — the menu only landed correctly when the frame happened to render at 1:1.
- **Pointer capture retargets the trailing click to the capturing element.** The map captured on `pointerdown` so drags could track outside the element — which meant every tap on a pin arrived as a tap on the *map*, hit the dismiss handler, and closed the callout instead of opening it. Every pin, every time. Fix: capture only once the gesture passes the drag threshold.
- **A cancelled Web Animation *rejects* its `finished` promise.** So an interrupted transition never ran its cleanup, and the departing screen kept its "still on stage" class — sitting there frozen until some later transition happened to involve it again. Each slide now registers its cleanup and the next one runs it before cancelling.
- **Duplicate ids across two arrays.** Added listings numbered 15–18 without noticing another array already used 15–18. `find()` returns the first match, so four of one person's items opened someone else's listing, and favouriting one toggled the wrong heart. All ids unique now.
- **A permanently-present element toggling `hidden` breaks existence checks.** Verified map callouts with `!!querySelector('.callout')` for a long stretch — always true, tested nothing. Check `.hidden`, not presence.

---

## Still open

- Swear Display is licensed and not bundled; Newsreader Italic stands in.
- Real photos — all imagery is CSS placeholder tiles designed to swap for `<img>`.
- Identity editing (name, avatar, pronouns) has no path; location is only editable during onboarding. All four belong behind the `...`.
- Message opens the inbox rather than a thread — no compose screen yet.
- Editing a post opens the composer un-prefilled.
- Empty states are invisible because the demo profile is fully populated. A real new user lands with sizes and location and three blank sections.
- One post (Double Dragon Tee) is mine but sits in the public array, so it appears in the feed and search while my others don't. Data-model call, not a bug.
