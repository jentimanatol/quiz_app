git --version
git add .
git commit -m "'Auto Commit"'"
git push origin main

:: === Tagging for GitHub Actions Release Build ===
git tag v1.3
git push origin v1.3
pause
