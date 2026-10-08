# Startup check investigation

The initial native payload run rejected the locally installed Windows Tesseract
banner `tesseract v5.5.0.20241111`: the first parser accepted only a numeric
banner without `v`. The corrected parser accepts both real upstream and Windows
installer forms, with a regression case for each. The final payload is rebuilt
and revalidated separately.

The installer tests ran concurrently with that blocked GUI smoke process and
correctly refused installation while PartSmith was running. The failed XML
retains this concurrency error. The owned smoke process was stopped; final
installer tests are run after the GUI exits. No user application was stopped.
