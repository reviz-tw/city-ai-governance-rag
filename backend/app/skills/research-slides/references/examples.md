# Examples of evidence becoming useful slides

These sources are synthetic teaching examples, not facts about a real city. Real output must use only the evidence supplied with the request and its actual IDs.

## A distinction is a comparison, not two vague summaries

Synthetic evidence: "Internal assistants prepare a draft for a staff member to check. Public-facing assistants need an escalation route when they cannot answer. Neither service may disclose personal data."

Weak page: title "AI governance"; body "Improve efficiency. Manage risk. Increase transparency."

Useful page:

- layout: comparison
- title: "The service audience changes the review requirement"
- takeaway: "Staff review and public escalation address different points of failure."
- columns: ["Safeguard", "Internal assistant", "Public-facing assistant"]
- rows: [["Response handling", "Staff check the draft", "Escalate unanswered questions"], ["Personal data", "Must not disclose", "Must not disclose"]]
- reasoning: evidence
- notes: "The source specifies staff review for internal drafts and an escalation route for public services. It does not establish which service is safer or provide comparative performance measurements."
- citations: the actual document/block pair for that passage

## A recommendation must be distinguished from an official procedure

Synthetic evidence: "The office requires privacy review and assigns final approval to the service owner. The report does not specify implementation order."

A process slide can propose: identify the proposed use → review privacy issues → seek the owner's decision. Its `reasoning` is `recommendation`, each step explains what to examine, and its notes explicitly say the sequence is a proposed way to apply the two stated requirements. It must not claim this is the office's mandated three-step process.

## Limited evidence warrants fewer pages

Synthetic evidence: "The checklist records vendor, model and version."

One useful briefing page can distinguish supplier identity from model/version traceability and explain what the form records. A short source quote can support it. Do not stretch this into six pages about performance, audits, procurement, costs and governance maturity: those topics are absent. Set `coverage_note` to explain why the requested six-page scope cannot be supported.

## Numbers must retain their meaning

Synthetic evidence: "In 2026, 20 applications were reviewed by Team A and 12 applications were reviewed by Team B."

A bar chart may compare 20 and 12, using the original unit "applications" and period "2026" and citing the exact sentence for each point. It cannot relabel these counts as risk scores, percentages, savings or service quality. Without comparable numbers, choose a qualitative layout.
