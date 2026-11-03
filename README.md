# RAM Monitor for Windows

This repository builds the supplied RAM Monitor Python desktop app into a standalone Windows executable using GitHub Actions. Python is installed only on GitHub's Windows build runner; it is not required on your PC.

## Get the EXE
1. Open the **Actions** tab.
2. Select **Build RAM Monitor for Windows**.
3. Click **Run workflow** and wait for the run to finish.
4. Open the completed run and download the **RAMMonitor-Windows** artifact.
5. Extract the artifact ZIP and run RAMMonitor.exe.

The source archive is stored as base64 text in `RAMMonitor-source.zip.b64`; the workflow decodes it on the runner before building.

Note: Some system-wide memory operations require Administrator privileges. Windows manages memory automatically; clearing caches may temporarily reduce performance.
