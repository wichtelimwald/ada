# Data classification — initial proposal

**Status:** Draft. Validate during product discovery and threat modeling.

The purpose is to reason consistently about storage, model context, logging, and cloud egress.

| Class | Examples | Default handling direction |
|---|---|---|
| Public | public documentation, public web content | normal processing; still treat content as untrusted instructions |
| Personal | preferences, ordinary conversation history, non-sensitive notes | local by default; user-controlled retention |
| Sensitive | private documents, contacts, screen content, location/history, personal communications | local by default; explicit need and disclosure before remote use |
| Secret | passwords, API keys, auth tokens, recovery codes, private keys | dedicated secret store; never normal memory/model context unless a narrowly scoped mechanism explicitly requires it |

Classification is about confidentiality, not trust. A public web page can be non-sensitive and still be malicious input.
