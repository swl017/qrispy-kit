---
name: plan-page
description: Show decisions, design alternatives, plans or experiment results to the user as an interactive HTML page in Lavish Editor instead of a chat message or a plan file, and record the answers back into the ticket. Use whenever the user asks to compare options so they can choose (even two options), to approve a plan, to review several items at once, or to interpret results with figures. Only where Lavish is available.
when_to_use: 'several decisions at once, "옵션 비교", "설계안 보여 줘", "계획 승인", "결과 해석", "정리 페이지", triage of many items, any reply that would be a wall of text.'
allowed-tools: Bash(npx -y lavish-axi@0.1.87:*)
---

# Decision and result pages (Lavish)

This skill applies only where Lavish (`lavish-axi`) or the viewer named in `<ticket root>/METHOD_LOCAL.md` is available; without one, put the decisions in `q_questions.md` with a recommendation each, as the `qrispy:ticket` skill says.

Lavish (`lavish-axi`, pinned at `0.1.87`, MIT) serves a local HTML file in the browser, lets the user choose, annotate and send feedback, and returns it to you. The page is a viewing and input surface; the record stays in the ticket's Markdown files.

Call it as `npx -y lavish-axi@0.1.87 …`. Never use `lavish-axi share`: it publishes to a public third-party host.

## 1. Build the page

1. Read the playbooks that match before writing HTML: `npx -y lavish-axi@0.1.87 playbook input` for any decision page, plus `comparison`, `plan`, `table` or `diagram` as the content needs.
2. Put the page in the ticket: `<ticket dir>/lavish/<name>.html`. Copy images it shows into the same folder and reference them by relative path.
3. Copy a template from this skill's `${CLAUDE_SKILL_DIR}/templates/` folder: `decision.html` for choices (radio, multi-select, resolved cards, recommendation marks, a note per card, a "fill with recommendations" button, one tracked-batch queue button) or `result.html` for results (risk card, figures, key table, the one claimable sentence, "what this does not show", and 수용 / 질문 / 재실행 요청 per result). Change only the `<title>` and the JSON in `<script id="page-data">`; the mechanics are shared. When the same questions also go into `q_questions.md`, generate both from one source so they cannot drift (for example one Python list that writes both the page and the file). Render once with a headless browser (for example `google-chrome --headless=new --screenshot`) at 420 px width before sending the URL.
4. Keep each card short: the question, two or three lines of context, options with the recommendation marked, and a note field. Put long rationale behind a "자세히" disclosure, not in the card.
5. Lead the page with what the user must decide and what happens next.

## 2. Open it and wait

1. `npx -y lavish-axi@0.1.87 <ticket dir>/lavish/<name>.html` prints a URL on `127.0.0.1`. Give the user the URL. If the user works over a remote connection (for example VSCode Remote), a URL printed in your shell is not forwarded automatically: tell them to forward the port in the **Ports** panel ("Forward a Port") and open `http://localhost:<port>/…`.
2. Wait with `npx -y lavish-axi@0.1.87 poll <file>` as a background command (`run_in_background`), which wakes you when feedback arrives. Do not use `nohup` or `&`. State the local time you started waiting. If the session restarted while a poll was waiting, the old listener cannot wake the new session: re-run the poll with `--takeover` (a plain re-run fails with `LISTENER_ACTIVE`).

## 3. Record the answers

1. Read the whole poll payload; the decisions are in its `data.items`. A result page's answer goes at the end of the slice note it names (`record_to`); a 재실행 요청 is never run before the user approves its cost (GPU go).
2. Record every submitted item verbatim in the ticket's Markdown (usually `q_questions.md`, under `> 사용자 답 (date, Lavish round N):`), with the user's notes copied word for word, and say what you did with each note.
3. Follow the `qrispy:ticket` skill's editing rules: a line-bounded pattern, heading count before and after, diff of the text outside the answers.
4. Account for every submitted ID before you report. Reply in the page with `npx -y lavish-axi@0.1.87 poll <file> --agent-reply-file <reply.md>` when another round follows, or `reply` when it does not. Report the elapsed time since you started waiting.
5. If the notes raise new questions, open a next round on the same page: fold the answered cards into a grey summary, add the new cards at the top, and mark them with Lavish's revision legend.
