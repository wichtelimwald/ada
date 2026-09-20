# Results — Action Ledger crash/recovery probe

**Status:** Prepared; execution pending.

## Pass criteria

- hard crash after provider commit leaves ledger in `executing`;
- restart reconciles rather than repeating the provider write;
- final ledger state becomes `committed`;
- provider effect count stays exactly one;
- denied operation produces zero provider writes;
- illegal transitions fail;
- stale concurrent state transition cannot claim the same operation twice;
- provider without reconciliation support yields `ambiguous` and no retry.
