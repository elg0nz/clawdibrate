# The Ongoing Weekly Loop

After the six-week pass, the machine runs on a weekly cadence. The point of a fixed cadence is that it makes the uncomfortable half — sourcing and follow-up — non-optional. Left unscheduled, product work always wins, because product work is more pleasant and feels like progress.

---

## The week

```
Monday      Pick 5 target users.
Tue–Wed     Run interviews or concierge deliveries.
Thursday    Ship one product change from observed pain.
Friday      Follow up with prior users.
            Ask for the next instance.
            Record who acted.
```

**One product change per week.** Not zero, not five. Zero means you're doing research instead of building; five means you're building from your own head, since you cannot have gotten five well-grounded signals in two days of conversations.

**Friday follow-up is the part people drop, and it's where repeat pull is manufactured.** A user who acted once and never hears from you again is a user you spent your best signal on and abandoned.

---

## Metrics to track

Vanity metrics are dangerous this early precisely because they're the ones that move on their own. Track behavior only. Full sheet: [`templates/weekly-metrics.md`](./templates/weekly-metrics.md).

```
Prospects contacted:
Users with a real instance of the problem:
Artifacts collected:
Concierge deliveries:
Outputs read:
Findings accepted:
Fixes applied:
Repeat instances sent:
Users asking for integration:
Product changes caused by feedback:
```

Two ratios matter more than any absolute count:

- **Applied / delivered** — is the output actionable?
- **Repeat / applied** — does acting once lead to acting again?

The second is the closest thing to a leading indicator of PMF in this kit. A high applied-rate with a zero repeat-rate means you built a one-time cleanup, not a workflow.

---

## The standing decision rule

Every feature must answer **yes** to at least one:

1. Does it help **collect** real instances of the failure you fix?
2. Does it make the output **more trusted**?
3. Does it make the fix **easier to apply or reject**?
4. Does it help users **rerun** after the next failure?
5. Does it **preserve evidence** for audit?

If not, delay it.

---

## Monthly review

Once a month, spend an hour on:

- **Segment check.** Are the users who act different from the users who don't? If yes, that difference is your real ICP — rewrite the Week 1 hypotheses around it.
- **Kill-rule check.** Re-read the [kill rules](./doctrine.md#kill-rules) and answer honestly whether any have triggered.
- **Backlog purge.** Delete every backlog item that fails the decision rule. Not "later" — delete. A backlog you never cut stops being a plan and becomes a museum.
- **Evidence hygiene.** Confirm every stored user artifact is still authorized and redacted (see [`evidence/README.md`](./evidence/README.md)).
