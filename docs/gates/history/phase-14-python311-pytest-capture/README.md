# Python 3.11 migration investigation

These failed exploratory runs are preserved with their original bytes. They
are not current passing evidence. The first run encountered invalid inherited
Windows standard-input handles under pytest capture. The second isolated
three failures: the batch error message contained an unescaped parenthesis,
the non-isolated IPC entry lost captured output on respawn, and the independent
replay worker lacked a checkout PYTHONPATH. The final run uses explicit
noninteractive child streams and the declared source path, with corrected batch
syntax. Current results are in phase-14-python311-source-results.xml.
