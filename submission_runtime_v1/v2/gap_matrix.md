# Knowledge Gap Matrix

Audit basis: V1 regression/historical failures, the approved source manifest,
and live V1/V2 tests. `Covered` means at least one approved public source is in
the Submission KB; it does not imply current/time-sensitive sufficiency.

| Area | High-frequency intents | V1 state | V2 state | Remaining gap |
|---|---|---|---|---|
| Enrollment/records | transcript, enrollment proof | Partial | Covered | Current office-hour changes |
| Graduation/degree | certificate copies, lost diploma/degree proof | Missing | Covered | English/overseas variants not audited |
| Courses/grades | grade rules, review/correction | Missing | Partial | Course selection, add/drop, exams, credits |
| Scholarships | eligibility and policy | Partial | Partial | Award-specific and current deadlines |
| Grants/loans | grant, national loan, post-loan management | Wrong-entity risk | Covered | Hardship recognition and current application windows |
| Campus network/IT | password, authentication, mail, VPN | Missing | Missing | Needs official public procedure sources |
| Library | opening, loan, renewal, databases, remote access | Historical intro only | Historical intro only | Current hours and service procedures |
| Housing | room change, rules, checkout, safety | Room change only | Covered | Repair/service entry and current application windows |
| Dining | canteens and services | Missing | Partial | Current hours/menu remain time-sensitive |
| Medical | campus hospital service | Missing | Partial | Department-specific/current appointment information |
| Campus card/transport/venues | card, bus, sports spaces | Missing | Missing | Official public service pages needed |
| Career development | student career service | Missing | Partial | Internship and event dates are current-sensitive |
| Research/innovation | labs, undergraduate research, startup | Missing | Missing | Official program sources needed |
| International exchange | programs and procedures | Missing | Missing | Official current program sources needed |

## Inclusion decision

Uploaded sources were restricted to manifest records with:

```text
source_type = public
review_status = approve
canonical path under sources/public
```

No restricted record was uploaded. No new web copy was scraped where an
approved canonical source already existed.
