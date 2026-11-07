# Demo script (~90 seconds)

Setup: `python -m backend.ingest --reset --exclude-family redis`, start API and UI.

1. **Problem (10s):** "3 AM, payments are failing. Priya has been here 8 months; the person who knew this system left."
2. **Memory OFF (15s):** load demo alert 1 (payments-api 5xx), toggle Memory OFF, Analyze. Generic "check logs, restart".
3. **Memory ON (25s):** same alert, Memory ON (or Compare). Cites INC-1042 / INC-1087, recommends rollback, warns restart did nothing.
4. **Feedback (10s):** click Worked with a note; open the new memory in the inspector/timeline.
5. **Learning (20s):** load demo alert 2 or 4 (other service, same family): rollback ranked first with higher confidence, cites the feedback event.
6. **Honesty (10s):** load demo alert 8 (node NotReady): low confidence, general guidance only.

Optional curve: run `ingest` again with the redis family (`python -m backend.ingest`), use demo alert 5, report "Didn't work" with the real fix ("increased maxmemory, changed eviction policy"), re-run alert 5 and show the failed fix demoted.

Close: "Every incident makes it smarter. Institutional memory that never leaves the company."
