# Interview Questionnaire — Ada

Status: confirmed scope for the first MVP iteration. This is a discovery baseline, not a completed architecture specification. Unresolved decisions are explicitly marked. The user chose to continue learning through use rather than finish every detailed question before starting.

## 1. Executive Summary

Ada is a public open-source personal assistant named after Ada Lovelace. Project-owned code is intended to use the MIT license. The initial real-world setting is a family: adults and children should be able to contribute information and receive appropriate assistance. Other households should be able to use the project from the beginning, although developer knowledge may initially be required.

The confirmed MVP supports local chat, forwarded email, calendar maintenance within granted permissions, conflict detection including approximate travel times, and personal or family briefings on request. It needs accessible persistent memory, privacy boundaries, independent permission enforcement, action logging, and understandable error recovery.

The first operating environment is an existing family MacBook Air with an M1 processor and 16 GB RAM. macOS is sufficient for the MVP. Deliberate pauses and laptop downtime are acceptable. Local processing is preferred; remote processing requires deliberate, appropriately scoped authorization.

Development and maintenance capacity is approximately one to two evenings per week. Direct school-system integrations, speech, generated conflict solutions, autonomous communication with third parties, and specialist personal workflows are deferred. The next step is a small end-to-end implementation and feasibility evaluation, not a comprehensive framework selection exercise.

## 2. Primary User and Problem

The first users are the initiating household, including guardians and children. Ada is also intended for other users, not solely as its maintainer's private tool. Early external adopters may have a developer background; a polished installation experience can follow later.

Current coordination happens through spoken exchanges and a shared calendar. Family members need a way to state appointments, wishes, and constraints without manually reconciling everything themselves.

Recurring examples include children's sports and music lessons, medical appointments requiring transport, business travel overlapping with office commitments, and arrangements involving grandparents or friends. The immediate value is a dependable shared understanding of commitments and conflicts. Over time, Ada should learn how the family resolves these situations and offer relevant suggestions.

Reasons to stop using Ada would include unreliability, loss of trust, excessive interruptions, failure to learn, or too much manual rework. Security and privacy must support practical use without unnecessary ceremony.

## 3. Core User Scenarios

The scenarios below describe intended behavior, not tested capabilities.

| Scenario | Trigger and expected interaction | Expected result | Limits and unacceptable failures |
| --- | --- | --- | --- |
| Capture an appointment | A family member writes to Ada, forwards a message or appointment, or uses local chat. | Ada identifies relevant details, asks necessary questions, and creates or updates the appointment within an existing permission. It reports what it actually did. | Do not confuse understanding with execution. Do not silently guess consequential missing details or duplicate an appointment. |
| Identify a coordination conflict | New information overlaps with known commitments or leaves insufficient travel time. | Ada identifies the conflict. Initially, the family resolves it; Ada learns from the resolution. | Do not assume all simultaneous appointments conflict. Transport responsibilities and shared-resource rules still need clarification. |
| Prepare for the day | An individual asks privately, or the family asks together at breakfast. | Explain what happens today, what needs packing, and what differs from the routine. | Respect the audience. Private appointments may contribute busy time without exposing their details. Do not invent packing requirements. |
| Answer a personal question | A family member asks Ada through an available channel. | Provide a concise, relevant answer using permitted context and memory. | Private conversations must not become visible to other family members merely because Ada serves the household. |
| Correct knowledge or an action | A user points out an error or edits the external memory. | Correct it, acknowledge the mistake, and use the correction in future behavior. | Do not silently reinstate an outdated fact or claim a correction succeeded when it did not. |
| Resume after a pause | Ada is reactivated after the laptop or assistant was unavailable. | For elapsed events, ask briefly what actually happened, for example whether the music lesson worked out. | Do not assume a scheduled event occurred successfully. Detailed handling of the remaining backlog is unresolved. |
| Resolve an urgent contradiction | Two sources give incompatible pickup times or similarly important details. | Request clarification, keep both possibilities in view, and favor safe precautions within granted authority. | A child must not be left waiting because Ada silently chose one interpretation. Additional contact channels may be used only if previously authorized. |

Normal email responses should arrive within a few minutes while Ada is operating. Exact local-chat latency and accuracy thresholds will be assessed through use. Ada should answer through the incoming channel, summarize its understanding or completed action, and include relevant questions or warnings.

## 4. Experience / "Jarvis Feeling" Requirements

Ada should sound human and natural rather than producing overly polished, generic assistant language. Responses should be quick, useful, factual, and appropriately concise. Uncertainty must be visible; assumptions may be proposed and agreed rather than presented as facts.

Personalization should adapt language, explanation depth, examples, humor, and expectations to the person. The initiating user prefers concise answers with some irony and nerdiness; children may need simpler explanations. Ada should consider relevant life context, such as school, work, holidays, life phase, weather, and time of day.

Learning should be observable: Ada changes its behavior appropriately and recalls relevant context. It should connect related topics without indiscriminately including unrelated personal information.

Personal and shared briefings are initially requested by users. Automatic daily briefings and last-minute departure alerts are not necessary for the first iteration. Presence or location surveillance is not wanted for this purpose.

Local text chat is required in the MVP. High-quality speech output is a later aspiration. Wake words, continuous listening, interruption handling, voice identification, visual presentation, and accessibility details remain unresolved. No UI framework has been selected.

## 5. Feature Prioritization

The priority vocabulary is: **MVP** — the minimum coherent version worth using; **V1** — important shortly afterward; **Later** — valuable but unnecessary early; **Nice to have** — optional enhancement; **Out / not now** — explicitly excluded or deferred.

The user confirmed the MVP below. No separate V1 release or Nice-to-have allocation was agreed. Later does not imply a delivery commitment. Where a wishlist item was not individually prioritized, that remains explicit.

| Feature / capability | User value | Priority | Why | Privacy / security notes |
| --- | --- | --- | --- | --- |
| Local text chat | Direct interaction, including offline use | MVP | Explicitly required; also provides a place for consequential approvals | Private context and authority must remain separate concerns. |
| Email intake and replies | Convenient family input using existing tools | MVP | The initial preferred external channel | Registered senders, trusted instructions separated from forwarded material, controlled recipients. |
| Forwarded messages and appointments | Useful source material without building every integration | MVP | Accepted initial replacement for direct school-system access | A forwarded instruction cannot grant authority. |
| Calendar maintenance within grants | Reduce manual entry and coordination work | MVP | Central everyday journey | Changes must respect permission scope and be logged; no arbitrary deletion. |
| Conflict detection with approximate travel times | Reveal practical scheduling problems | MVP | Overlap alone is insufficient | Start with family-confirmed estimates; avoid implied tracking. |
| Personal and family briefings on request | Explain today's commitments and preparation | MVP | Confirmed daily-use scenario | Audience-sensitive disclosure; private details stay private. |
| Accessible, correctable persistent memory | Continuity and learning | MVP | Needed for context, routines, and corrections | External readable/editable memory; no additional hidden persistent memory. |
| Permissions, private areas, logging, recovery | Make the family service trustworthy | MVP | Required boundaries around the main journey | Permission enforcement independent of the model. |
| Pause and resume | Share the laptop with ordinary family work | MVP | Explicit operating requirement | Do not silently continue paused work elsewhere. Detailed resume policy remains open. |
| Direct extraction from school systems | Reduce forwarding and missed school information | Later | Useful, but forwarding is accepted initially | Each integration needs a defined access and disclosure scope. |
| Suggested conflict solutions | Reduce the family's planning effort | Later | Initially show conflicts and learn from human solutions | Suggestions do not expand execution authority. |
| Autonomous communication and coordination with third parties | Eventually arrange agreed solutions | Later | Explicitly deferred from the first iteration | Requires recipient, representation, scope, and disclosure controls. |
| Speech and additional messaging / device-assistant channels | More natural and convenient access | Later | Email and local chat cover the first journey | Listening, bystanders, and identity requirements are unresolved. |
| Complex collective-decision workflows | Support agreement, consent/no-objection, majority, and multi-person choices | Later; precise scope unresolved | Desired on a topic-by-topic basis, not all needed for the first journey | Explicitly establish participants and the applicable rule. |
| Book writing, professional social-media support, multi-project coding, financial coaching | Personal specialist assistance | Later; order unresolved | Wishlist retained, excluded from the confirmed first iteration | Separate private/work contexts and task-specific authority; sensitive finance data. |
| Autonomous coding implementation and quality control | Execute a jointly agreed project plan | Later | Explicit long-term aspiration | Broad computer authority requires separate evaluation. |
| Shopping lists, meal-order reminders, leisure planning, birthdays/messages, weather/clothing, car allocation, broader research | Additional everyday assistance | Unresolved; outside the confirmed MVP | Desired scenarios were listed but not individually prioritized | Do not infer permission to purchase, send messages, or expose personal routines. |
| Rich character development and broader personalization | Make Ada feel familiar and adaptive | Desired; depth by release unresolved | Basic memory is in the MVP; a full personality system was not scoped | Learned behavior must not alter permissions or override user choices. |
| Last-minute departure alerts | Timely prompts | Out / not now for MVP | Requested briefings and existing calendar reminders suffice initially | Do not introduce presence surveillance. |
| Polished installation for non-developers | Broader adoption | Later | Developer knowledge is acceptable initially | Signing, packaging, and the eventual update experience remain open. |
| Assistant-managed backups | Reduce system administration effort | Out / not now | Backups belong to the surrounding system and its operator | Ada may help with system maintenance later if authorized. |
| Usage telemetry and error reports sent to the Ada project | Project diagnostics | Out | Explicitly rejected | Local action logs are a separate requirement, not permission to transmit reports. |
| Additional hidden persistent memory | None accepted | Out | The user requires memory to remain outside Ada | Operational caches and logs need clearly defined boundaries. |

## 6. MVP End-to-End Journey

This journey describes the agreed scope; setup mechanics remain undecided.

1. **Establish the household context.** Configure the relevant people, registered addresses, private/shared scopes, calendars, and permissions. Early users may perform developer-oriented setup.
2. **Receive an input.** A parent forwards a school appointment or submits it through local chat. Ada distinguishes the direct user instruction from quoted or forwarded content.
3. **Understand it.** Extract relevant facts, consult only needed permitted memory, and ask about material ambiguity or contradiction.
4. **Apply authority.** A narrowly authorized calendar action may proceed. If permission is missing, obtain an appropriate approval; broad or risky grants must be made directly in Ada.
5. **Maintain the calendar.** Perform the permitted operation, avoid duplicate execution, and report the actual result through the same channel.
6. **Identify a conflict.** Compare relevant commitments and family-confirmed approximate travel times. Highlight the problem without independently arranging a solution.
7. **Learn from the resolution.** The family decides what to do. Ada corrects the schedule or context within its authority and retains relevant permitted knowledge in the external memory.
8. **Answer a daily briefing request.** Provide the individual or family view of today's commitments, packing needs supported by known information, and departures from routine.

The journey must also support correction and resumption after partial failures. Local conversation and memory-based answers should work without internet. Remote email/calendar operations and offline cached data require separate handling; offline access to those datasets is unresolved.

The scope was challenged before confirmation. Integration automation, speech, independent solution generation, and specialist workflows were removed from the first iteration. The remaining calendar, memory, audience, and approval behavior still forms a substantial project for the available maintenance time.

## 7. Memory and Personalization Requirements

- Persistent memory must live outside Ada and be human-readable and directly editable without Ada. Changes made outside Ada must be respected. No backend or storage format has been chosen.
- There must be no additional independent or hidden persistent memory inside Ada. Permissible transient context, reconstructible indexes, and the relationship to mandatory action logs remain architecture questions.
- The default preference is automatic learning from relevant messages and appointments, except material explicitly marked secret or not to be stored. Exact handling of those labels remains to be specified.
- Credentials must not be remembered automatically. Explicitly requested storage is possible but requires especially sensitive handling. The storage mechanism is unresolved.
- Ada may learn routines gradually and may conduct an optional kickoff interview. Related context should be used when relevant, within access boundaries.
- Contradictions must be raised and clarification sought. Until resolved, Ada should retain awareness of both possibilities and favor safe handling within authorized limits.
- Remembered facts should have useful, coarse source attribution. A detailed provenance trail is unnecessary for continuously adapting attributes such as conversational style.
- After extracting relevant information, messages can remain in an archive. Ada must not actively search that archive unless explicitly asked.
- The agreed configurable message lifecycle is **two years of retention, then three months in trash, then permanent deletion**. This supersedes the earlier shorter proposal. The exact retention-clock convention and responsible system remain open.
- Derived memories remain when their source messages are deleted. A source reference does not imply that the deleted original remains recoverable.
- Relearning removed information should happen only when there is a reason, not through routine archive rescanning. The detailed policy for deliberate forgetting remains unresolved.
- Backup responsibility belongs to the operator and external memory system. Ada-managed backup is not required. Export format, synchronization, restore semantics, and memory expiry are unresolved.

Sensitive local storage and permission to disclose that information are distinct. No blanket approval to send remembered material to remote services follows from permission to remember it.

## 8. Privacy, Sync, and Remote-Service Requirements

Local processing is preferred where practical. Cloud processing may be used deliberately when local capability is insufficient, but Ada must obtain a matching approval if none already exists. Apply **need to know**: send only information necessary for the specific task, not entire histories or memory collections by default.

Credentials, health information, and personal financial information are identified as particularly sensitive. Explicit exceptions for health and financial information must remain possible, with a warning and informed approval. The intended disclosure should identify the information, recipient service, and purpose. Whether credentials have any exceptional cloud-disclosure path was not separately resolved; it must not be assumed.

Authority over sensitive disclosure follows these rules:

- Conservative default: an adult decides about their own data.
- In the initiating household, the guardians may represent each other. Other households must explicitly establish representation rights at setup or when needed.
- Whether representation includes explicitly private content must itself be clarified; it is not automatically included.
- Children cannot independently authorize sensitive cloud disclosure. Guardian authorization is necessary.
- Grandparents decide about their own data; their involvement does not confer authority over the rest of the household.

Users choose and accept their own email and calendar hosting. This does not authorize onward disclosure to another service or model. Information stored locally can still leave a device through processing or integrations; local storage and no data egress are different properties. A personally administered hosted server is also a distinct trust boundary from a device at home.

The user proposed a dedicated Ada identity with email, calendar, and contacts, plus audience-specific addresses for individuals and groups such as the family, parents, children, or grandparents. Messages could reach Ada and the intended people, while users subscribe to the appropriate calendars. This is an integration idea, not a selected account or routing architecture. The underlying requirements are convenient intake, clear intended audiences, and individual/shared calendar access. A recipient address identifies an audience; it does not authenticate the sender or grant authority. Exact alias-copying rules and contact access remain to be defined.

No usage telemetry or error reports may be sent to the Ada project. Automatic software-update checks are a user decision that Ada must clarify. Automatic installation, model/artifact downloads, and their metadata have not been specified.

Sync behavior, backup locations, remote-service retention/training/access conditions, detailed separation of private and work data, and future microphone/camera bystander behavior remain open. The no-tracking preference for reminders is confirmed; comprehensive sensing is not an MVP requirement.

## 9. Autonomy, Recovery, and Permission Requirements

Start restrictively. Expand authority through explicit grants for individual actions and, later, defined patterns or areas. Familiarity, learned preferences, and successful past execution do not enlarge permissions. Ada may propose an action and request approval. Relevant activities must be logged.

Guardians have equal standing in family decisions. Children's ability to approve actions may grow through guardian-authorized scopes or individual decisions; where Ada acts on a child's behalf, the child's own agreement remains relevant within that authority. Private areas are needed for everyone, including children.

Collective decisions may use agreement, no-objection, unanimity, or majority rules, with active requests or discussion at an appropriate opportunity. The user wants to define these consciously per topic as needs arise, rather than design an exhaustive governance system up front.

| Action / situation | Required authority or behavior |
| --- | --- |
| Read submitted information and relevant permitted memory | Within the established task and audience scope; this is not permission to inspect unrelated material. |
| Create a recognized appointment or maintain a calendar | May proceed automatically within a previously granted scope. Recognized school appointments were discussed as such a scope. |
| Delete appointments | No arbitrary deletion. Cancellation and deletion scopes still require explicit definition. |
| Approve a simple, individual action by email | Only a direct instruction from an authorized registered sender; not text in forwarded or quoted sections. Ask explicitly if uncertain. |
| Grant general, broad, or risky authority | Direct interaction in Ada through the local system/UI/chat. Enforcement must be independent of the model. |
| Identify an approver in the initiating household's MVP | Laptop access is restricted to guardians; no additional identity check is required there. This assumption must not be generalized to other installations. |
| Respond to an unknown external sender | No reply without approval. Inform the relevant registered family members instead. |
| Send messages or act in someone's name | Requires the applicable explicit grant; autonomous third-party coordination is deferred. |
| Use an additional channel for an urgent unresolved issue | Allowed if that channel has already been authorized. No unrestricted escalation. |
| Read the message archive | Only on explicit request. |
| Perform general computer, terminal, installation, purchase, or financial actions | Not authorized by the MVP scope. Detailed classifications remain for later discovery. |

Websites cannot issue permissions. Forwarded email sections cannot issue permissions. The final discussion established the broader requirement that the model cannot create its own authorization. Handling of other untrusted surfaces—documents, screenshots, files, and tool output—must be specified consistently during security design; a complete surface-by-surface policy was not finalized.

The visible email From field alone is insufficient evidence of authority. Sender verification remains a technical evaluation task. Likewise, accepting the household's trusted-laptop assumption does not resolve how Ada selects a personal context or protects one adult's private content from another.

Errors must be acknowledged honestly, corrected, and used to improve future behavior. A humorous apology can fit, depending on seriousness. After partial failure, resume at the failed step when possible, first checking whether an operation already succeeded despite missing confirmation. If completion remains impossible, report the failure. Retry limits, undo guarantees, and log retention are unresolved.

## 10. Platform, Hardware, Distribution, and Availability Requirements

| Topic | Confirmed constraint or unresolved point |
| --- | --- |
| First platform | macOS is sufficient for the MVP. Exact supported versions are unresolved. |
| Available first-use hardware | MacBook Air, Apple M1, 16 GB RAM. Free storage and sustainable workload limits are not yet measured. |
| Shared-device use | It is the family laptop, with access restricted to guardians. Ada must be easy to pause so normal work can take precedence. |
| Availability | Continuous operation is not required. Downtime when the laptop sleeps, closes, or is otherwise unavailable is acceptable. |
| Offline use | Local chat and answers using local memory should continue. Email/calendar caching remains open. |
| Installation | Developer knowledge may be assumed initially. Polished setup comes later. |
| Other hardware ideas | An old Mac mini, an iPhone, and an existing hosted server in Germany were discussed. None was selected as the MVP execution environment. |
| Long-term platforms | Preserve the question of other operating systems and server deployment for evaluation. Permanent macOS restriction could be acceptable if justified by concrete advantages. |
| Mobile access | Desired access through convenient channels does not establish a requirement for a dedicated mobile app. |
| Resource use | Ada must yield the laptop for ordinary work. CPU, memory, storage, energy, and battery budgets remain unquantified. |
| Startup, distribution, updates | Startup behavior, signed builds, packaging, update installation, and release support remain open. Update checking must be a clarified user choice. |

No programming language, UI framework, platform architecture, model runtime, provider, or deployment-management tool has been selected.

## 11. Capability Success Criteria

These are product acceptance intentions, not evidence that a selected technology meets them. The user explicitly deferred numeric local-chat response-time targets until practical use.

| Capability | Intended success | Still to evaluate |
| --- | --- | --- |
| Interaction / "Face" | Local chat works; replies are concise and distinguish understanding, questions, and completed actions; broad approvals happen directly in Ada; pausing is accessible. | Visible processing states, accessibility, identity/context switching, and exact local-chat latency. |
| Reasoning / "Brain" | Interpret ordinary family messages, identify relevant facts, expose conflicts and uncertainty, use only relevant context, and avoid unsupported assumptions. | Quality on representative real tasks; local hardware suitability; what needs authorized remote assistance. |
| Persistent context / "Memory" | Recall useful permitted facts, honor outside edits and corrections, surface contradictions, and support relevant personalization. | Retrieval accuracy, expiry, concurrent changes, forgetting semantics, and allowable derived indexes. |
| Actions / "Hands" | Maintain calendars within grants, report actual outcomes, avoid duplicate operations, and recover from partial failures. | Supported appointment forms, update/cancellation handling, and recovery guarantees. General computer control is deferred. |
| Policy / "Guard" | Enforce grants independently of model decisions, reject authority from websites/forwarded content, protect private areas, and log actions. | Sender authentication, private-content representation, approval binding, revocation, and log access/retention. |
| Remote-data egress | Necessary information only; obtain the required scoped authorization; warn before sensitive exceptions; no silent expansion to another recipient or purpose. | Data classification and minimization quality, remote-service terms, and enforcement across future integrations. |
| Email | Respond substantively within a few minutes during normal operation, through the same channel and to permitted recipients. | Provider integration, outage recovery, delivery failure behavior, and actual measured performance. |
| Speech input / "Ears" and output / "Voice" | Later: natural interaction and very good speech output. | Languages, wake behavior, interruption, latency, accessibility, and bystander privacy. |
| Perception / "Eyes" | No required MVP capability identified. | Whether any later scenario justifies screen or camera access. |

Task-specific capabilities and memory should be selected economically. The user wants relevant context and capabilities rather than unnecessarily large prompts or indiscriminate use of all available skills. Specialized or combined capabilities are evaluation possibilities, not chosen component boundaries.

## 12. Non-Goals / Explicitly Deferred

- A complete general-purpose personal assistant in the first iteration.
- Autonomous resolution of family scheduling conflicts or unapproved communication with third parties.
- Direct school-system integrations, speech, specialist coding/writing/finance workflows, and broad computer automation in the MVP.
- Continuous availability, deployment to every platform, or polished non-developer setup at launch.
- Location/presence surveillance to power routine reminders.
- Backup management by Ada in the initial product.
- Telemetry or error reporting to the Ada project.
- Additional hidden persistent memory, unbounded access, or authority inferred from encountered content.
- Using Mark LIV source code or assets as implementation reference. It remains product/UX inspiration only; a security principle reported by the user does not change that boundary.

## 13. Open Product Questions

These are recorded for iterative discovery; they are not all prerequisites for beginning work.

- Exact personal/family calendar arrangement, ownership, and how private busy-time information participates in conflict detection.
- How transport responsibility, shared cars, and other family resources are represented; when learned travel estimates should be revised.
- How to choose the acting person's private context on the trusted shared laptop without unwanted disclosure.
- Approval scopes for modifications, cancellations, deletion, representation, and mixed-person sensitive data; revocation behavior.
- Whether any credential disclosure to a cloud model is ever permitted; precise treatment of secret versus do-not-store labels.
- Local-chat history retention, selective forgetting, memory expiry, source changes, and how logs/caches coexist with external-only memory.
- Offline mail/calendar access and stale-data warnings; handling of pending, rather than already elapsed, tasks after a pause.
- Remote-service conditions, ongoing cost limits, sync, software/model downloads, and update installation.
- Measurable reliability targets and the amount of remaining manual work that would make Ada worth using.
- Exact V1, Later, and Nice-to-have ordering beyond the confirmed MVP exclusions.
- Future voice, sensing, accessibility, mobile use, and work/private separation.

## 14. Architecture Decisions for Later Evaluation

No implementation is preferred in this document. Use decision matrices and ADRs when a real choice becomes necessary. Do not assign numeric weights without discussing them with the user.

Confirmed constraints include the intended MIT licensing of project-owned code, the M1/16 GB first-use environment, independent permission enforcement, external accessible memory, privacy boundaries, no project telemetry, and the initial maintenance budget. The legal and usage compatibility of dependencies, models, and assets must be assessed separately; project MIT intent does not determine their licenses.

| Decision | Constraining product requirements | Evaluation criteria | When needed |
| --- | --- | --- | --- |
| Execution architecture and programming language | macOS MVP; pause support; limited resources; possible future server/cross-platform use | OS dependencies, maintainability, portability, security boundaries, integration effort | Before the first coherent implementation |
| Local interaction and approval mechanism | Offline chat, direct broad/risky approvals, trusted-laptop exception, eventual private contexts | Usability, authority enforcement, accessibility, packaging, identity support | First iteration |
| Local model and runtime; optional remote assistance | M1/16 GB, useful family reasoning, no unsupported claims, selective context, approved egress | Task quality, latency, memory use, offline operation, licensing, replaceability, cost | Early representative feasibility experiment |
| Memory representation and retrieval | External readable/editable memory, individual scopes, provenance, corrections, no hidden independent memory | Portability, retrieval quality, edit reconciliation, access control, deletion behavior, operating effort | First iteration |
| Email/calendar integration | Existing user-chosen hosting, registered addresses, forwarded inputs, safe calendar maintenance | Authentication, provider compatibility, audience routing, duplicate prevention, failure recovery, least privilege | First iteration |
| Permission enforcement and action records | Independent from model, progressively granted scopes, children/guardians, mandatory logging | Bypass resistance, scope clarity, revocation, usability, privacy of records, testability | Before enabling consequential writes |
| Remote-data boundary | Need to know, warnings and sensitive exceptions, per-person/representation rules | Data egress, minimization, retention, provider access/training, regional constraints, verification | Before enabling any model or service disclosure beyond agreed hosting |
| Agent/capability orchestration and integrations | Reuse established mechanisms; activate relevant capabilities and memory only | Complexity, security, interoperability, maturity, resource efficiency, replaceability | When concrete scenarios require it |
| Packaging and updates | Developer setup initially; user-controlled checks; later easier adoption | Maintenance burden, provenance, distribution, security response, platform reach | Minimal packaging first; polished distribution later |
| Speech and perception | Deferred experience goals; no established sensing requirement | Quality, local operation, privacy, latency, interruption, permissions, resource use | Only when promoted into scope |

Across comparisons, consider privacy/egress, least privilege, UX, quality, hardware use, OS integration, cross-platform potential, accessibility, maturity and security response, integration compatibility, packaging, testability, licensing, replaceability, and cost. Relative importance and additional hard gates remain to be agreed; not every criterion was independently ranked in this interview.

## 15. Risks and Blind Spots

These are analysis points, not newly approved requirements.

- **Scope versus capacity:** Even the reduced MVP combines messaging, calendars, memory, privacy, and authority management. One to two evenings per week favors narrow, demonstrable increments.
- **Hardware versus quality:** The available laptop is known; satisfactory local reasoning and latency are not yet demonstrated. A shortfall does not automatically authorize cloud use.
- **Calendar reliability:** Repeated messages, recurrence, stale updates, ambiguous dates, and partially completed writes could create incorrect commitments. These need focused validation once supported behavior is defined.
- **Identity and private contexts:** Guardian-only laptop access supports the accepted MVP approval shortcut but does not by itself identify which guardian is speaking or who should see private information.
- **Email and encountered instructions:** A registered address is a product-level identity rule, not a complete authentication design. Trusted senders can also forward untrusted material.
- **Learning without observation:** Calendar entries do not establish actual travel duration or attendance. Learning needs suitable feedback without turning into surveillance or constant questioning.
- **Sensitive combinations:** Removing names may leave identifying or sensitive context. Information about several people raises unresolved authority questions.
- **Retention tension:** Source deletion deliberately leaves memories intact. Explicit forgetting, editable memory, action records, and any derived indexes need consistent boundaries.
- **Availability:** Accepted pauses can delay urgent information. Ada must not be relied upon as an always-available safety service under this operating model.
- **Future autonomy:** Broader computer control, financial guidance, third-party contact, and collective decision workflows introduce requirements not settled by the MVP grants.

External research during discovery supports treating sensitive disclosure and model-only restrictions cautiously. [OWASP's sensitive-information guidance](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/) discusses exposure risks, least privilege, and the limits of prompt restrictions. [NCSC guidance](https://www.ncsc.gov.uk/blog-post/chatgpt-and-large-language-models-whats-the-risk) recommends avoiding sensitive inputs to public LLMs and examining provider handling for cloud services. These sources informed discussion; the household's agreed policies and unresolved exceptions are recorded separately above.

## 16. Recommended Next Discovery/Architecture Step

Proceed iteratively from this confirmed baseline. The following sequence is a recommendation, not an already selected implementation plan:

1. **Create a small representative scenario set.** Include an ordinary school appointment, a travel-time conflict, a private appointment in a family briefing, a contradictory pickup time, and a correction. Define the expected outcome with the family. Use synthetic or appropriately redacted examples for any public project material.
2. **Evaluate the smallest local path on the actual MacBook.** Check whether ordinary chat, relevant memory use, and appointment understanding are useful at acceptable speed. Measure performance before choosing a broader stack.
3. **Make only the decisions needed for the first working slice.** Compare the relevant options against the confirmed constraints, record the reasoning in ADRs, and keep deferred decisions open.
4. **Build one complete family journey.** Move from an authorized input through a safe calendar operation and conflict notice to a useful briefing, including correction and clear reporting. Enable consequential actions only with the required permission boundary.
5. **Review real use together.** Judge usefulness, trust, interruptions, manual rework, and operating effort. Adjust the baseline and prioritize the next increment from evidence.

The agreed direction is to learn on the go while keeping scope, privacy, and authority explicit. This document can be revised as those practical lessons emerge.
