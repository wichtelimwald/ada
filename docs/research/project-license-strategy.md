# Technology / governance evaluation — Ada project license

**Status:** Research framing complete; no license change made  
**Date checked:** 2026-09-20

## 1. Question

Ada's project-owned code is currently MIT licensed.

The maintainer wants a deliberate decision on whether Ada should remain MIT or move early to another permissive license, especially Apache-2.0.

The decision must be made before a large external contributor base exists, because relicensing becomes materially harder once many independent copyright holders have contributed.

## 2. Important patent clarification

Apache-2.0's patent grant does **not** mean a contributor licenses patents they do not own or control.

Section 3 applies only to patent claims:

- licensable by that contributor; and
- necessarily infringed by that contributor's contribution alone, or by combining it with the work to which it was contributed.

Therefore:

- if a contributor owns no relevant patents, they are not granting non-existent rights;
- if an unknown third party owns a patent that the project unintentionally infringes, Apache-2.0 does not give Ada or its users a license to that third-party patent;
- Apache-2.0 also does not turn an accidental third-party infringement into a patent that Ada can "pass on";
- the explicit grant primarily protects downstream users against contributors later asserting their own relevant patent claims against use of their contribution;
- the license includes a patent-litigation termination mechanism.

This is general open-source licensing analysis, not legal advice for a specific patent dispute.

## 3. Hard gates

Any selected project license should:

1. be OSI-approved and widely understood;
2. allow commercial and private use;
3. allow modification and redistribution;
4. not impose source-disclosure/copyleft obligations on Ada users;
5. permit Ada to depend on and distribute compatible MIT/Apache/BSD components;
6. be practical for an international public GitHub project;
7. keep contribution mechanics understandable for occasional contributors;
8. not add avoidable restrictions that conflict with Ada's intended permissive ecosystem.

## 4. Candidates

### A — MIT

Current license.

**Strengths**

- extremely short and familiar;
- permissive commercial/private use;
- low administrative burden;
- easy for individual contributors and adopters to understand;
- common in Python/AI ecosystems.

**Trade-offs**

- no explicit patent-license clause in the text;
- less explicit contribution/patent treatment than Apache-2.0;
- attribution obligation is simple but minimal.

### B — Apache License 2.0

Permissive OSI-approved license with explicit copyright and patent grants.

**Strengths**

- explicit contributor patent grant;
- explicit treatment of contributions;
- explicit patent-litigation termination;
- permissive commercial/private use;
- widely accepted by companies and infrastructure projects;
- clear NOTICE/attribution mechanism.

**Trade-offs**

- substantially longer and more legalistic than MIT;
- redistribution/NOTICE and modification-notice obligations are more detailed;
- project maintainers must keep licensing metadata disciplined;
- patent language can look intimidating to casual contributors even though it grants only claims they can actually license.

### C — BSD 3-Clause

Permissive OSI-approved control option.

**Strengths**

- concise and mature;
- permissive;
- includes a non-endorsement clause.

**Trade-offs**

- like MIT, no explicit patent grant in the license text;
- provides little benefit over MIT for Ada's specific concerns;
- somewhat less common than MIT in Ada's immediate Python/AI dependency ecosystem.

## 5. Dependency compatibility

Ada's own project license does not need to match every dependency license.

Examples in the current architecture:

- PydanticAI: MIT
- DBOS candidate: MIT
- Cedar Policy: Apache-2.0
- cedarpy: Apache-2.0
- Temporal candidate: MIT

Both MIT and Apache-2.0 can generally coexist with these permissive dependencies when their respective attribution/license obligations are preserved.

Third-party code remains under its own license even if Ada's project-owned code uses a different permissive license.

## 6. Proposed decision criteria — weights not yet agreed

| Criterion | Proposed weight | Rationale |
| --- | ---: | --- |
| Patent/IP clarity for contributors and downstream users | **30%** | Ada is infrastructure/security software and may be adopted commercially. |
| Adoption / commercial friendliness | **20%** | Keep use by individuals, companies and academia straightforward. |
| Simplicity / contributor understandability | **20%** | Ada should remain approachable to occasional OSS contributors. |
| Distribution / compliance burden | **15%** | Avoid unnecessary release/admin friction for a small-maintainer project. |
| Ecosystem / dependency compatibility | **10%** | Must fit the Python/AI/open-source stack cleanly. |
| Future relicensing / governance practicality | **5%** | Early choice should age well as contributors accumulate. |
| **Total** | **100%** | |

## 7. Preliminary qualitative comparison

| Property | MIT | Apache-2.0 | BSD-3-Clause |
| --- | --- | --- | --- |
| OSI approved | yes | yes | yes |
| Permissive commercial use | yes | yes | yes |
| Explicit patent grant | no explicit clause | **yes** | no explicit clause |
| Patent-litigation termination | no | **yes** | no |
| Explicit contribution treatment | minimal | **stronger** | minimal |
| Text/administrative simplicity | **strongest** | lowest of these three | strong |
| NOTICE mechanism | no special NOTICE mechanism | **yes** | no special NOTICE mechanism |
| Non-endorsement clause | no | no | **yes** |
| Typical corporate familiarity | high | **high** | high |

## 8. Questions to answer before scoring

1. How much do we value explicit patent clarity relative to a shorter contributor-facing license?
2. Do we expect commercial/company adoption to be a significant goal?
3. Do we want every contribution to carry Apache-2.0's explicit patent grant as a deliberate project policy?
4. Are Apache NOTICE/modification obligations acceptable for Ada's small-maintainer release process?
5. Does the maintainer prefer minimal legal text unless a concrete benefit justifies more complexity?

## 9. Migration timing

If Ada changes its project-owned license, doing so **before** a substantial external contributor base exists is operationally much simpler.

A future migration after many contributors may require consent or provenance analysis for code owned by other copyright holders.

No license change should be made until this evaluation is accepted explicitly.

## 10. Primary references

- Apache License 2.0: https://www.apache.org/licenses/LICENSE-2.0
- Apache license application guidance: https://www.apache.org/legal/apply-license
- Apache patent-grant FAQ: https://www.apache.org/licenses/cla-faq.html
- MIT License (OSI): https://opensource.org/license/mit
- BSD 3-Clause (OSI): https://opensource.org/license/BSD-3-clause
- OSI approved licenses: https://opensource.org/licenses
