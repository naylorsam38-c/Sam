# CATEGORY_SUMMARY — Event Ticketing

category: Event Ticketing (id 27, slug event-ticketing)
exemplar: Eventbrite / Ticketmaster

This category folder holds evidence from two runs: the pre-registry
three-category pilot (`iyanuashiri/meethub`, `fossasia/eventyay`,
`pyconsk/django-konfera`, `suenkler/django-tickets`,
`DefinitelyNotAnAssassin/TicketManagementSystem` -- same real-world domain,
run before CATEGORY_REGISTRY.json/exemplar feature matching existed), and
this registry-driven validation run (`iyanuashiri/meethub` re-verified at
the same commit, `fossasia/eventyay` re-recorded, plus newly discovered
`SalahEddine-Ghannouch/GetTicket_Events_Django`). All candidates from both
runs are kept per Section 11/24 ("do not discard inspected candidates").

candidates inspected (this run): 3
candidates inspected (pre-registry pilot, same category domain, kept above): 5
candidates passing hard gates (ADMITTED), either run: 0
candidates rejected, either run: 6 distinct repositories (meethub and
eventyay appear in both runs; not double-counted)

## Rankings (eligible candidates only -- feature match first, quality score tiebreak)

(none -- no candidate from either run passed the hard gates)

## Rejected, with reasons (this run)
  iyanuashiri/meethub:
    - Rule B: source publishes no REST API documentation
  SalahEddine-Ghannouch/GetTicket_Events_Django:
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation
  fossasia/eventyay:
    - Rule C licence: UNRESOLVED -- see researcher_notes is not permissive (allowed: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0)
    - Rule B: source publishes no REST API documentation

## Rejected, with reasons (pre-registry pilot, kept for the complete record)
  DefinitelyNotAnAssassin/TicketManagementSystem:
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule C licence: (not recorded) is not permissive
  pyconsk/django-konfera:
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation
  suenkler/django-tickets:
    - Rule A datastore: needs postgresql, source says (not recorded)
    - Rule B: source publishes no REST API documentation

## Selected candidate
**NONE ADMITTED**

Reason: every inspected candidate across both runs failed at least one hard admission rule -- see each candidate's own REPORT.md for which
