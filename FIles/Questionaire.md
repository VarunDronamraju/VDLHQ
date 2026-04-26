Questionnaire (Q)
Q: What is the primary bottleneck right now?
A: Time spent on calls and manual coordination


Q: What is the target state in 3–6 months?
A: Automated workflows with reduced human intervention


Q: Which part of the process should be fixed first?
A: Data capture, processing, and usage


Q: How many leads are handled per day?
A: Around 20 per day, with a peak of 30


Q: How are leads currently handled?
A: Through calls


Q: What is the desired communication model?
A: Structured inquiry with automated responses and selective calls


Q: Where should data be stored?
A: Centralized PostgreSQL or RDBMS


Q: What data needs to be stored?
A: Leads, clients, inquiries, bookings, notes, and workflow state


Q: How should client history be managed?
A: Through persistent profiles with reusable data and notes


Q: How should internal coordination work?
A: Through a company dashboard with clear status tracking


Q: How should clients interact with the system?
A: Through a client-facing dashboard or CRM


Q: What replaces manual coordination?
A: Workflow-driven system with status tracking


Q: What is not needed immediately but required in the future?
A: Advanced permit automation (core lifecycle is already included in MVP as tracking, not full automation)


Q: How should permit handling be designed later?
A: As an extension layer on top of the core system


Q: What is the core problem type?
A: Data and workflow structuring problem


Q: What is the first system to build?
A: Data layer with structured intake and CRM


Q: What should follow after the data layer?
A: Workflow engine (state machine), then dashboards, then automation layers


Q: Where do most leads come from?
A: Likely inbound inquiries via calls and website


Q: Where do leads usually drop off?
A: During initial communication or due to delayed follow-ups


Q: What happens during a typical call?
A: Requirement gathering, clarification, and initial qualification


Q: Which parts of the call are repetitive?
A: Collecting basic client info and shoot requirements


Q: Can part of the call be replaced?
A: Yes, through structured pre-call inquiry forms


Q: How are leads currently tracked?
A: Informally or manually, without a defined pipeline


Q: Is there a defined lead pipeline today?
A: No structured pipeline exists


Q: What are the ideal lead stages?
A: Inquiry → needs_info → ready → matched → booked → permit_pending → permit_submitted → permit_in_review → permit_approved → coordination → closed → archived


Q: How is booking status tracked today?
A: Through manual follow-ups and communication


Q: What causes delays in the process?
A: Manual coordination and lack of visibility


Q: How do team members coordinate internally?
A: Through calls or messages without a central system
Q: Is there a single source of truth for data?
A: No, data is scattered across tools or conversations


Q: How often is data reused?
A: Rarely, leading to repeated data collection


Q: What errors occur due to manual entry?
A: Inconsistent, incomplete, or duplicated data


Q: Do clients request frequent updates?
A: Yes, due to lack of visibility


Q: What frustrates clients the most?
A: Delays and lack of transparency


Q: Is there a system for handling complaints?
A: No structured complaint or ticketing system


Q: How are follow-ups currently handled?
A: Manually, depending on the person


Q: Are follow-ups consistent?
A: No, they vary based on individual effort


Q: How can follow-ups be improved?
A: Through automated and scheduled messaging


Q: Is partial inquiry data captured?
A: No, partial leads are often lost


Q: How can partial leads be used?
A: Capture → follow-up for missing data → move to ready


Q: What is missing in the current website?
A: Structured inquiry capture and conversion flow


Q: Should the website be the first touchpoint?
A: Yes, as a structured intake layer


Q: What should the internal dashboard show?
A: Leads, bookings, workflow status, and tasks


Q: What should the client dashboard show?
A: Inquiry status, updates, and history
Q: How should workflow status be tracked?
A: Through defined stages with clear ownership


Q: What defines a production-ready system here?
A:Persistent data, State-driven workflow engine (C1), Controlled automation (not fully autonomous), Clear ownership of transitions, Retry + fallback mechanisms


Q: What is the biggest immediate improvement?
A: Reducing call load through structured intake


Q: What enables scalability in this system?
A: Standardized workflows and centralized data


Q: What is the long-term system goal?
A: A system-driven, partially automated operations platform


Q: What should not be overbuilt initially?
A: Complex infrastructure or full automation


Q: What should be prioritized for MVP?
A: Intake, CRM, and workflow tracking


Q: What role does AI play initially?
A: Assistive, not fully autonomous


Q: Where should AI be applied first?
A: Intake parsing, readiness assessment, matching, and controlled communication (rewrite only)


Q: What ensures system reliability?
A: Structured data, clear workflows, and tracking


Q: What reduces dependency on individuals?
A: System-defined processes and dashboards


Q: What is the final business transformation?
A: From manual operations to a structured, scalable system


Q: How are follow-ups handled?
A: Mark inactive after 7 days of no response
Human can reactivate
Nurturing continues in background


Q: What defines a “ready” lead?
A: All required fields complete, clear requirements, usable budget range


Q: What fields are mandatory in inquiry?
 A: Contact, shoot type, dates, budget, location type


Q: Is inquiry editable after submission?
 A: Yes, user can update details which re-triggers workflow


Q: What triggers workflow execution?
 A: New inquiry, form update, status change, no response, human action


Q: Who owns final decision-making?
 A: Human (agents assist but do not finalize decisions)


Q: When does human intervention happen?
 A: After lead becomes ready, during booking confirmation, and edge cases


Q: How is workflow state stored?
 A: PostgreSQL with fields: lead.status, booking.status, workflow.stage


Q: What happens if automation fails?
 A: Retry → fallback → human intervention


Q: What is the basic booking trigger?
 A: Client confirms matched location and proceeds


Q: Who controls workflow transitions?
 A: C1 WorkflowEngine  all state transitions are centralized and enforced here


Q: Are workflows linear?
 A: No  system supports loops, retries, re-entry, and inactivity paths


Q: Can matching fail? What happens then?
 A: Yes  one clarification loop is triggered, then fallback to manual ops if still unresolved


Q: Are permits instant?
 A: No  permits follow a lifecycle: pending → submitted → in_review → approved/rejected


Q: Does communication happen only on state change?
 A: No  also triggered by reminders, inactivity, and permit updates


Q: Does LLM control decisions?
 A: No  LLM assists interpretation, ranking, and messaging only. All decisions are deterministic


Q: What happens if client rejects a match?
 A: Lead returns to ready state → matching re-triggered


Q: Where can leads drop off?
 A: needs_info, matched, permit stages  each has follow-up or nurturing handling




