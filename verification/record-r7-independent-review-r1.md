# R7 Recorder source and saved-evidence review

No material blocker found in staged Recorder `75333074…`. The delta changes binary export capture to 4MiB chunks with final fsync, adds an explicit timeout boolean, and preserves the earlier timeout reason when later pump/drain errors produce exit125. Ordinary text display/raw capture, exact success-line checks, subprocess groups and accounting remain unchanged. Native R2 uses its separate frozen Recorder1a7 copy.

Independently rehashed saved receipts/raw/exports for the twelve reported small controls; exact bytes and receipt bindings agree. The combined timeout plus two open pipes case is mocked and proves metadata/failure behavior only; no actual service/orphan claim follows. No test was rerun, no module imported, and no process signal or proof tool was used by this review.

Linux speed and original failure causality remain unmeasured. Separate systemd service lifetime controls remain the driver responsibility. Companion JSON pins source/control hashes, saved artifact bindings and review resources.
