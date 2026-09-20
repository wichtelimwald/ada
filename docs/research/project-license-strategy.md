# Technology / governance evaluation — Ada project license

**Status:** Decision accepted — retain MIT; no relicensing required  
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

### D — OSC License 1.0

New OSI-approved permissive license whose canonical text is German and whose permission grant is intentionally close to MIT, with liability language written specifically for German-law constraints.

**Strengths**

- OSI approved in 2025;
- permissive commercial/private use;
- simple MIT-like permission model;
- liability language explicitly designed for German law.

**Trade-offs**

- very new compared with MIT/Apache/BSD;
- canonical license text is German, while Ada is intended as an international OSS project;
- materially less familiar to companies, contributors and tooling ecosystems today;
- no explicit patent grant in the license text.

Because Ada's hard gates include being internationally practical and widely understood, OSC is retained as a useful control/reference but is not currently a finalist.

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

## 6. Agreed decision criteria

The maintainer explicitly reduced the weight of patent concerns and increased the importance of simple use, including commercial use.

| Criterion | Weight | Rationale |
| --- | ---: | --- |
| Patent/IP clarity for contributors and downstream users | **20%** | Still relevant, but not the dominant concern. |
| Adoption / commercial friendliness | **25%** | Individuals and companies should be able to use Ada commercially without unusual friction. |
| Simplicity / contributor understandability | **25%** | License obligations should be easy for users and occasional contributors to understand. |
| Distribution / compliance burden | **15%** | Avoid unnecessary release/admin friction for a small-maintainer project. |
| Ecosystem / dependency compatibility | **10%** | Must fit the Python/AI/open-source stack cleanly. |
| Future relicensing / governance practicality | **5%** | Early choice should age well as contributors accumulate. |
| **Total** | **100%** | |

## 7. Qualitative comparison

| Property | MIT | Apache-2.0 | BSD-3-Clause | OSC-1.0 |
| --- | --- | --- | --- | --- |
| OSI approved | yes | yes | yes | yes |
| Permissive commercial use | yes | yes | yes | yes |
| Explicit patent grant | no explicit clause | **yes** | no explicit clause | no explicit clause |
| Patent-litigation termination | no | **yes** | no | no |
| Explicit contribution treatment | minimal | **stronger** | minimal | minimal |
| Text/administrative simplicity | **strongest** | lowest of the finalists | strong | MIT-like permission model, longer liability text |
| Special NOTICE mechanism | no | **yes** | no | no |
| Non-endorsement clause | no | no | **yes** | no |
| Typical international familiarity | **very high** | **very high** | high | low / new |
| Canonical language | English | English | English | German |

## 8. Scoring

Scale:

- **5 — excellent fit**
- **4 — good fit**
- **3 — acceptable with meaningful trade-offs**
- **2 — weak on this criterion**
- **1 — poor fit**

The scores below assess license text and practical project use. They are architecture/governance judgment, not legal advice.

| Criterion | Weight | MIT | Apache-2.0 | BSD-3-Clause |
| --- | ---: | ---: | ---: | ---: |
| Patent/IP clarity | 20% | 2 | **5** | 2 |
| Adoption / commercial friendliness | 25% | **5** | **5** | 4.5 |
| Simplicity / contributor understandability | 25% | **5** | 3 | 4 |
| Distribution / compliance burden | 15% | **5** | 3 | 4.5 |
| Ecosystem / dependency compatibility | 10% | **5** | **5** | 4.5 |
| Governance / contribution clarity | 5% | 3 | **5** | 3 |
| **Weighted total / 100** | **100%** | **86** | **84** | **76** |

OSC-1.0 is not included in the finalist score because it currently misses Ada's own “widely understood / international public project” hard-gate intent. It remains a useful German-law reference and should be reconsidered if adoption/familiarity materially increases.

### Interpretation

**MIT — 86:** best match to the maintainer's stated preference for uncomplicated private and commercial use, short obligations, low distribution overhead and broad ecosystem familiarity. Its main weakness is the lack of an explicit patent grant/contribution framework in the license text.

**Apache-2.0 — 84:** nearly tied. It is strong for commercial adoption and materially clearer on patent and contribution rights, but imposes more text, redistribution conditions and NOTICE/modification handling. Under the maintainer's reduced patent weighting, those advantages no longer outweigh the simplicity cost.

**BSD-3-Clause — 76:** valid and mature, but does not materially improve Ada's patent/contribution position over MIT and adds the non-endorsement condition without solving a current Ada problem.

The MIT/Apache difference is small enough that the score should not be treated as mathematical certainty. The practical tie-break is whether Ada deliberately wants Apache-2.0's explicit patent/contribution framework enough to accept its additional compliance surface.

## 9. Decision

The maintainer accepted the result on 2026-09-20:

> **Retain the MIT License for Ada's project-owned code.**

Rationale:

- MIT best matches Ada's current priority on simple private and commercial use;
- its obligations are short, familiar, and low-overhead for a small-maintainer OSS project;
- Apache-2.0 remains a credible alternative, but its explicit patent/contribution advantages do not currently outweigh its additional compliance surface under the agreed weighting;
- BSD-3-Clause and OSC-1.0 do not provide a stronger overall fit for Ada at this time.

This decision does not relicense third-party dependencies. Each dependency retains its own license and notice obligations.

Re-open if Ada's contributor/governance model changes materially, corporate adoption creates a concrete need for explicit patent grants, or applicable legal/licensing practice changes.

## 10. Migration timing

If Ada changes its project-owned license, doing so **before** a substantial external contributor base exists is operationally much simpler.

A future migration after many contributors may require consent or provenance analysis for code owned by other copyright holders.

No license change should be made until this evaluation is accepted explicitly.

## 11. Primary references

- Apache License 2.0: https://www.apache.org/licenses/LICENSE-2.0
- Apache license application guidance: https://www.apache.org/legal/apply-license
- Apache patent-grant FAQ: https://www.apache.org/licenses/cla-faq.html
- MIT License (OSI): https://opensource.org/license/mit
- BSD 3-Clause (OSI): https://opensource.org/license/BSD-3-clause
- OSC License 1.0 (OSI): https://opensource.org/license/osc-1.0
- OSI approved licenses: https://opensource.org/licenses
