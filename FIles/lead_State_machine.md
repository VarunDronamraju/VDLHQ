Lead State Machine
new
 └─→ needs_info          (readiness score below threshold or fields missing)
      └─→ inactive        (no client response after 7+ days)
           └─→ archived   (no response after extended period)
      └─→ ready           (client provides missing fields, readiness passes)
 └─→ ready               (readiness score passes threshold on first attempt)
      └─→ matched         (location shortlist sent, awaiting client decision)
           └─→ ready      (client rejects shortlist, re-matching triggered)
           └─→ inactive   (no client response after 7+ days at matched stage)
           └─→ booked     (client confirms location)
                └─→ permit_pending    (permit checklist generated, process initiated)
                     └─→ permit_submitted  (ops team submits permits to authority)
                          └─→ permit_in_review  (authority reviewing)
                               └─→ permit_approved   (permits cleared)
                                    └─→ coordination  (shoot logistics underway)
                                         └─→ closed   (shoot completed)
                               └─→ permit_rejected   (flagged for manual resolution)
                                    └─→ permit_pending (resubmission after resolution)

C1 WorkflowEngine owns every transition. Inactivity is detected at needs_info, matched, and permit stages. Reminders and nudges are sent by C1 via A5 independently of state changes.
