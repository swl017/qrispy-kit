---
name: cite
description: Check what may be quoted from a ticket before putting any of its numbers, results or conclusions into a paper, a slide, a report or another ticket. Use every time a ticket's result is about to be quoted, summarised or compared, even if you think you remember it.
when_to_use: '"논문에 넣자", "이 수치 써도 돼?", "결과 요약", "슬라이드에 넣자", quoting ticket numbers, claim sentences, figures.'
argument-hint: <ticket id>
---

# Quoting a ticket

Never quote a ticket's number or conclusion from memory, from an auto-memory note, or from a slice note. Quote only what its citation boundary allows, and cite the source file with it. Check:

1. **The ticket's `CITE.md`** — `qrispy cite <id>` prints it. It is the only source of citation boundaries. Quote only rows in "인용 가능", with their source path; never anything in "인용 금지"; ask the user about "출처 미확인" rows. If it prints a ⚠ line (the ticket moved after the boundary was judged), do not quote: tell the user the boundary needs re-judging.
   For a ticket of an external system (`external_systems` in `qrispy.json`), read `<its root>/<NNN-slug>/CITE.md` directly; `qrispy` does not index those systems.
2. **No `CITE.md`** — `qrispy cite` lists the files to read (closeout, latest review response). Read the claim-safe conclusion there, quote only that, and tell the user the ticket has no citation boundary yet.

A citation record that a repository has retired (named in `<ticket root>/METHOD_LOCAL.md`) is history, never the current boundary.

Then:

- Check the ticket's status (`qrispy show <id>`). A provisional closeout, open blocking findings, or a withdrawn artifact changes what may be said.
- Apply the claim discipline of the document you are writing into: each paper or report keeps its own in its root `CLAUDE.md`, and the repository's common claim rules are in its `CLAUDE.md` and `<ticket root>/METHOD_LOCAL.md`.
- Write the citation with its source: ticket, file and section (for example "<SYSTEM> NNN, `z_closeout.md` §2").
- If what you were about to quote is not in the boundary, do not quote a nearby number instead. Tell the user what is missing.
